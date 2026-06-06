import random
from copy import deepcopy
from card_defs import (
    CARD_DEFS, LANDMARK_DEFS,
    WHEAT_SYMBOL_CARDS, CUP_SYMBOL_CARDS, BREAD_SYMBOL_CARDS, GEAR_SYMBOL_CARDS,
)
from game_config import HARBOUR_GAME

_LANDMARK_BY_ID = {lm['id']: lm for lm in LANDMARK_DEFS}


# ── Dice RNG seam ────────────────────────────────────────────────────────────
# All dice go through this module-level Random so tests can make rolls
# deterministic via seed(). Production leaves it unseeded (system entropy).
_rng = random.Random()


def seed(n):
    """Seed the dice RNG for deterministic rolls (used by tests)."""
    _rng.seed(n)


def roll_die():
    """Roll a single six-sided die through the seedable RNG."""
    return _rng.randint(1, 6)


# ── State creation ─────────────────────────────────────────────────────────────

def create_initial_state(players_info, config=HARBOUR_GAME):
    """Build a fresh game state for the given version `config`.

    Defaults to HARBOUR_GAME so existing callers and the characterization
    harness are unchanged. Everything version-specific (which cards/landmarks
    exist, the starting hand, starting coins) comes from `config`.
    """
    num_players = len(players_info)
    players = []
    for p in players_info:
        players.append({
            'seat':      p['seat'],
            'name':      p['display_name'],
            'user_id':   p.get('user_id'),   # None for guests; used to attribute scores
            'coins':     config.starting_coins,
            'cards':     dict(config.starting_cards),
            # Renovation (Sharp Phase B): {card_id: closed_copies}. A closed copy
            # skips its next activation, then reopens. Per-copy count, so multiple
            # copies renovate independently. Part of state → persists via save/load.
            'renovation': {},
            # Invested coins accumulated on a card (Sharp Phase C1, Tech Startup):
            # {card_id: coins}. Persists across turns; activation pays it out but
            # does not clear it. Part of state → persists via save/load.
            'investments': {},
            'landmarks': [
                {'id': lm['id'], 'name': lm['name'], 'cost': lm['cost'],
                 'built': lm['pre_built'], 'effect': lm['effect']}
                for lm in (_LANDMARK_BY_ID[lid] for lid in config.landmark_ids)
            ],
        })

    # Supply: 6 per regular card, num_players per purple card — only the cards
    # this version includes.
    supply = {}
    for card_id in config.establishment_ids:
        card = CARD_DEFS[card_id]
        supply[card_id] = num_players if card['type'] == 'Purple Major' else 6

    start_seat = min(p['seat'] for p in players)

    return {
        'phase':          'roll',
        'version':        config.name,
        'active_seat':    start_seat,
        'last_roll':      None,
        'last_dice':      [],
        'doubles':        False,
        'ap_active':      False,
        'ap_used':        False,
        # Tech Startup (Sharp C1): the active player may invest at most once per
        # turn. Reset on turn change (and on an Amusement Park extra turn).
        'tech_invest_used': False,
        # Per-roll scratch: active copies of interactive green cards (Demolition,
        # Moving), set by resolve_cards each roll. See _interactive_copies.
        'interactive_active_copies': {},
        'pending_prompt': None,
        'players':        players,
        'market':         [CARD_DEFS[cid] for cid in config.establishment_ids],
        'supply':         supply,
        'card_defs':      CARD_DEFS,
        'winner':         None,
        'game_seq':       0,
        'log':            [],
    }


# ── Helpers ────────────────────────────────────────────────────────────────────

def player_by_seat(state, seat):
    for p in state['players']:
        if p['seat'] == seat:
            return p
    return None

def has_landmark(player, lm_id):
    return any(lm['id'] == lm_id and lm['built'] for lm in player['landmarks'])

def card_count(player, card_id):
    return player['cards'].get(card_id, 0)

def landmarks_built(player):
    """Count a player's built landmarks, excluding City Hall.

    City Hall is a pre-built safety net, not a constructed landmark, so it's
    excluded — the same rule calculate_scores uses for the win/score count. This
    is the primitive the Sharp landmark-count cards (Corn Field, General Store,
    French Restaurant, Private Club) condition on. Base-agnostic: works whether
    the base has 4 landmarks (Basic, no City Hall) or 6 (Harbour, excludes it)."""
    return sum(1 for lm in player['landmarks'] if lm['built'] and lm['id'] != 'city_hall')

def take_coins(giver, receiver, amount):
    actual = min(giver['coins'], max(0, amount))
    giver['coins']    -= actual
    receiver['coins'] += actual
    return actual

def give_coins(player, amount):
    player['coins'] += max(0, amount)

def add_log(state, msg):
    state['log'].append(msg)
    state['log'] = state['log'][-15:]

def opponents(state):
    active = state['active_seat']
    return [p for p in state['players'] if p['seat'] != active]


# ── Renovation (Sharp Phase B) ───────────────────────────────────────────────
# A closed copy skips exactly one activation and then reopens. We track a closed
# *count* per (player, card_id) so copies renovate independently (physical tokens).

def closed_copies(player, card_id):
    return player.get('renovation', {}).get(card_id, 0)

def active_copies(player, card_id):
    """Owned copies that actually pay/activate (owned minus closed)."""
    return max(0, card_count(player, card_id) - closed_copies(player, card_id))

def close_for_renovation(player, card_id, copies):
    """Mark `copies` more copies of card_id closed (capped at owned)."""
    if copies <= 0:
        return
    reno = player.setdefault('renovation', {})
    reno[card_id] = min(card_count(player, card_id), reno.get(card_id, 0) + copies)

def _reopen(player, card_id):
    """Reopen all closed copies of card_id (their skipped activation has come up)."""
    player.get('renovation', {}).pop(card_id, None)


# ── Card resolution ────────────────────────────────────────────────────────────

def resolve_cards(state, roll):
    """
    Process all card effects for this roll (Tuna Boat excluded — handled interactively).
    Returns ({seat: [change_str, ...]}, [transfer_str, ...]) where transfers are
    broadcast to all players ("X pays N to Y (Card)").
    """
    changes   = {}
    transfers = []
    active = player_by_seat(state, state['active_seat'])
    all_players = state['players']

    def gain(player, amt, name):
        if amt > 0:
            changes.setdefault(player['seat'], []).append(f"+{amt} {name}")

    def lose(player, amt, name):
        if amt > 0:
            changes.setdefault(player['seat'], []).append(f"-{amt} {name}")

    # ── 0. Renovation — closed copies whose number is up reopen now, paying 0 ──
    # Compute, per (seat, card_id), the copies that PAY this roll (owned − closed),
    # then reopen the closed ones (this matching roll is their skipped activation).
    # When nothing is renovated, paying == owned and behavior is unchanged.
    paying = {}
    for player in all_players:
        for card_id, count in list(player['cards'].items()):
            if roll in CARD_DEFS[card_id]['dice']:
                closed = closed_copies(player, card_id)
                paying[(player['seat'], card_id)] = max(0, count - closed)
                if closed:
                    _reopen(player, card_id)
                    add_log(state, f"{player['name']}'s {CARD_DEFS[card_id]['name']} reopens from renovation")

    def act_of(player, card_id, count):
        # Paying copies for this roll (set in the renovation pass); falls back to
        # owned for safety on any card the pass didn't see.
        return paying.get((player['seat'], card_id), count)

    # ── 1. Red — opponents, counter-clockwise from active ──────────────────────
    seats = sorted(p['seat'] for p in all_players)
    active_idx = seats.index(state['active_seat'])
    for i in range(1, len(seats)):
        opp_seat = seats[(active_idx - i) % len(seats)]
        opp = player_by_seat(state, opp_seat)
        if not opp:
            continue
        for card_id, count in list(opp['cards'].items()):
            card = CARD_DEFS[card_id]
            if card['type'] != 'Red Restaurant':
                continue
            if roll not in card['dice']:
                continue
            if 'requires_landmark' in card and not has_landmark(opp, card['requires_landmark']):
                continue
            act = act_of(opp, card_id, count)
            if act <= 0:
                continue  # all copies closed for renovation — reopened above, pays 0

            # Sharp restaurants gate on the active (roller) player's landmark
            # count rather than paying a flat per-copy amount.
            if card_id == 'private_club':
                # Take the roller's entire balance, once, if they're far ahead
                # (3+ landmarks). Extra copies are redundant — it's already all.
                amount = active['coins'] if landmarks_built(active) >= 3 else 0
            elif card_id == 'french_restaurant':
                # 5 per copy, but only against a roller with 2+ landmarks.
                amount = act * 5 if landmarks_built(active) >= 2 else 0
            else:
                per_copy = {'cafe': 1, 'family_restaurant': 2, 'sushi_bar': 3,
                            'hamburger_stand': 1, 'pizza_joint': 1}.get(card_id, 1)
                amount = act * per_copy
                if has_landmark(opp, 'shopping_mall') and card['symbol'] == 'cup':
                    amount += act

            taken = take_coins(active, opp, amount)
            if taken:
                add_log(state, f"{opp['name']} takes {taken}🪙 from {active['name']} ({card['name']})")
                gain(opp, taken, card['name'])
                lose(active, taken, card['name'])
                transfers.append(f"{active['name']} pays {taken}🪙 to {opp['name']} ({card['name']})")

    # ── 2. Blue — every player (Tuna Boat resolved separately) ────────────────
    for player in all_players:
        for card_id, count in list(player['cards'].items()):
            card = CARD_DEFS[card_id]
            if card['type'] != 'Blue Primary':
                continue
            if card_id == 'tuna_boat':
                continue
            if roll not in card['dice']:
                continue
            if 'requires_landmark' in card and not has_landmark(player, card['requires_landmark']):
                continue
            act = act_of(player, card_id, count)
            if act <= 0:
                continue

            if card_id == 'mine':
                amt = act * 5
            elif card_id == 'apple_orchard':
                amt = act * 3
            elif card_id == 'mackerel_boat':
                amt = act * 3
            elif card_id == 'vineyard':
                amt = act * 3  # Sharp: flat +3, no condition (anyone's turn)
            elif card_id == 'corn_field':
                # Sharp: +1 only while the owner is behind (1 or fewer landmarks).
                amt = act if landmarks_built(player) <= 1 else 0
            else:
                amt = act  # wheat_field, ranch, forest, flower_garden

            if amt:  # a gated card (corn_field) can resolve to 0 — stay quiet then
                give_coins(player, amt)
                add_log(state, f"{player['name']} gets {amt}🪙 ({card['name']})")
                gain(player, amt, card['name'])

    # ── 3. Green — active player only ─────────────────────────────────────────
    for card_id, count in list(active['cards'].items()):
        card = CARD_DEFS[card_id]
        if card['type'] != 'Green Secondary':
            continue
        if roll not in card['dice']:
            continue
        if 'requires_landmark' in card and not has_landmark(active, card['requires_landmark']):
            continue
        act = act_of(active, card_id, count)
        if act <= 0:
            continue

        if card_id == 'loan_office':
            # Sharp C1: negative activation — pay 2 to the bank per active copy,
            # floored at 0 (locked default). Build-time +5 is in the build handler.
            pay = min(active['coins'], act * 2)
            if pay:
                active['coins'] -= pay
                add_log(state, f"{active['name']} pays {pay}🪙 to the bank (Loan Office)")
                lose(active, pay, 'Loan Office')
            continue

        mall = has_landmark(active, 'shopping_mall')
        bonus = act if (mall and card['symbol'] in ('bread', 'cup')) else 0

        if card_id == 'bakery':
            amt = act * 1 + bonus
        elif card_id == 'convenience_store':
            amt = act * 3 + bonus
        elif card_id == 'cheese_factory':
            ranches = card_count(active, 'ranch')
            amt = act * ranches * 3
        elif card_id == 'furniture_factory':
            gears = card_count(active, 'forest') + card_count(active, 'mine')
            amt = act * gears * 3
        elif card_id == 'farmers_market':
            wheat = sum(card_count(active, c) for c in WHEAT_SYMBOL_CARDS)
            amt = act * wheat * 2
        elif card_id == 'flower_shop':
            amt = act * card_count(active, 'flower_garden')
        elif card_id == 'food_warehouse':
            cups = sum(card_count(active, c) for c in CUP_SYMBOL_CARDS)
            amt = act * cups * 2
        elif card_id == 'general_store':
            # Sharp: +2 only while the active player is behind (1 or fewer landmarks).
            amt = act * 2 if landmarks_built(active) <= 1 else 0
        elif card_id == 'soda_bottling_plant':
            # Sharp: +1 per Red (Restaurant) establishment OWNED by ALL players,
            # owner's reds included (ownership, not active — renovated reds count).
            red_total = sum(
                cnt
                for pl in all_players
                for cid, cnt in pl['cards'].items()
                if CARD_DEFS[cid]['type'] == 'Red Restaurant'
            )
            amt = act * red_total
        elif card_id == 'winery':
            # Sharp Phase B: 6 per Vineyard owned, then the copies that activated
            # close for renovation (so the next roll-9 reopens them, paying 0).
            # "Vineyards you own" counts owned copies regardless of renovation.
            amt = act * 6 * card_count(active, 'vineyard')
            close_for_renovation(active, 'winery', act)
            add_log(state, f"{active['name']}'s Winery closes for renovation")
        else:
            amt = 0

        if amt:
            give_coins(active, amt)
            add_log(state, f"{active['name']} gets {amt}🪙 ({card['name']})")
            gain(active, amt, card['name'])

    # ── 4. Purple — active player only ────────────────────────────────────────
    for card_id, count in list(active['cards'].items()):
        card = CARD_DEFS[card_id]
        if card['type'] != 'Purple Major':
            continue
        if roll not in card['dice']:
            continue
        if act_of(active, card_id, count) <= 0:
            continue  # uniformity: Majors aren't renovated today, but stay consistent

        if card_id == 'stadium':
            for opp in opponents(state):
                taken = take_coins(opp, active, 2)
                if taken:
                    add_log(state, f"{active['name']} takes {taken}🪙 from {opp['name']} (Stadium)")
                    gain(active, taken, 'Stadium')
                    lose(opp, taken, 'Stadium')
                    transfers.append(f"{opp['name']} pays {taken}🪙 to {active['name']} (Stadium)")

        elif card_id == 'publisher':
            for opp in opponents(state):
                symbol_cards = sum(
                    card_count(opp, cid)
                    for cid in opp['cards']
                    if CARD_DEFS[cid]['symbol'] in ('cup', 'bread')
                )
                taken = take_coins(opp, active, symbol_cards)
                if taken:
                    add_log(state, f"{active['name']} takes {taken}🪙 from {opp['name']} (Publisher)")
                    gain(active, taken, 'Publisher')
                    lose(opp, taken, 'Publisher')
                    transfers.append(f"{opp['name']} pays {taken}🪙 to {active['name']} (Publisher)")

        elif card_id == 'tax_office':
            for opp in opponents(state):
                if opp['coins'] >= 10:
                    tax = opp['coins'] // 2
                    taken = take_coins(opp, active, tax)
                    if taken:
                        add_log(state, f"{active['name']} takes {taken}🪙 from {opp['name']} (Tax Office)")
                        gain(active, taken, 'Tax Office')
                        lose(opp, taken, 'Tax Office')
                        transfers.append(f"{opp['name']} pays {taken}🪙 to {active['name']} (Tax Office)")

        elif card_id == 'tech_startup':
            # Sharp C1: each opponent pays the active player the total invested on
            # the card. The investment persists (not cleared on activation).
            invested = active.get('investments', {}).get('tech_startup', 0)
            for opp in opponents(state):
                taken = take_coins(opp, active, invested)
                if taken:
                    add_log(state, f"{active['name']} takes {taken}🪙 from {opp['name']} (Tech Startup)")
                    gain(active, taken, 'Tech Startup')
                    lose(opp, taken, 'Tech Startup')
                    transfers.append(f"{opp['name']} pays {taken}🪙 to {active['name']} (Tech Startup)")

        elif card_id == 'park':
            # Sharp C1: pool every player's coins and split equally; the remainder
            # (when it doesn't divide evenly) goes to the active player (locked default).
            total = sum(p['coins'] for p in all_players)
            share = total // len(all_players)
            remainder = total - share * len(all_players)
            for p in all_players:
                before = p['coins']
                p['coins'] = share + (remainder if p['seat'] == active['seat'] else 0)
                delta = p['coins'] - before
                if delta > 0:
                    gain(p, delta, 'Park')
                elif delta < 0:
                    lose(p, -delta, 'Park')
            add_log(state, f"{active['name']} pools and splits all coins equally (Park)")

    # ── 5. City Hall — active player at 0 coins gets 1 (only if they own it) ──
    # Harbour pre-builds City Hall for everyone, so this fires as before there;
    # the Base game has no City Hall, so the safety net correctly does not apply.
    if active['coins'] == 0 and has_landmark(active, 'city_hall'):
        give_coins(active, 1)
        add_log(state, f"{active['name']} gets 1🪙 (City Hall)")
        gain(active, 1, 'City Hall')

    # Stash this roll's pre-reopen active-copy counts for the interactive green
    # cards (Demolition, Moving). Section 0 has already reopened any renovated
    # copies, so _set_interactive_phase can't recompute these — it reads them here
    # to fire exactly the number of active copies (renovation contract).
    state['interactive_active_copies'] = {
        cid: paying.get((state['active_seat'], cid), 0)
        for cid in ('demolition_company', 'moving_company')
    }

    return changes, transfers


# ── Win condition ──────────────────────────────────────────────────────────────

def check_win(state):
    active = player_by_seat(state, state['active_seat'])
    if all(lm['built'] for lm in active['landmarks']):
        state['winner'] = active['seat']
        state['phase']  = 'finished'
        state['scores'] = calculate_scores(state)
        add_log(state, f"🏆 {active['name']} wins!")
        return True
    return False


# ── Turn advancement ───────────────────────────────────────────────────────────

def advance_turn(state):
    seats = sorted(p['seat'] for p in state['players'])
    idx = seats.index(state['active_seat'])
    state['active_seat']    = seats[(idx + 1) % len(seats)]
    state['phase']          = 'roll'
    state['last_roll']      = None
    state['last_dice']      = []
    state['doubles']        = False
    state['ap_active']      = False
    state['ap_used']        = False
    state['tech_invest_used'] = False
    state['pending_prompt'] = None


def calculate_scores(state):
    rows = []
    for p in state['players']:
        built = landmarks_built(p)
        rows.append({'seat': p['seat'], 'name': p['name'],
                     'user_id': p.get('user_id'),
                     'landmarks_built': built, 'coins_at_end': p['coins'],
                     'is_winner': p['seat'] == state.get('winner')})
    rows.sort(key=lambda r: -r['landmarks_built'])
    return rows


# ── Action handler (entry point called from main.py) ──────────────────────────

def handle_action(state, seat, msg):
    """
    Process one player action. Returns:
        {'broadcast': True}              — state changed, broadcast to all
        {'broadcast': True, 'prompt': …} — state changed + send a prompt to active player
        {}                               — nothing to do (wrong turn / invalid)
    """
    event        = msg.get('event')
    active_seat  = state['active_seat']
    active       = player_by_seat(state, active_seat)

    # ── Roll ───────────────────────────────────────────────────────────────────
    if event == 'roll' and seat == active_seat and state['phase'] == 'roll':
        dice_count = 2 if (msg.get('dice_count', 1) == 2 and has_landmark(active, 'train_station')) else 1
        dice = [roll_die() for _ in range(dice_count)]
        total = sum(dice)
        doubles = (len(dice) == 2 and dice[0] == dice[1])

        state['last_dice']  = dice
        state['last_roll']  = total
        state['doubles']    = doubles
        state['ap_active']  = doubles and has_landmark(active, 'amusement_park')

        add_log(state, f"{active['name']} rolls {'🎲' * dice_count} → {total}")

        # Harbor bonus check
        if total >= 10 and has_landmark(active, 'harbor'):
            state['pending_prompt'] = {'type': 'harbor_bonus', 'roll': total}
            state['phase'] = 'harbor_prompt'
            return {'broadcast': True, 'prompt': {
                'id':   'harbor_bonus',
                'text': f"You rolled {total}. Harbor: add +2 to make it {total + 2}?",
            }}

        # Radio Tower check
        if has_landmark(active, 'radio_tower'):
            state['pending_prompt'] = {'type': 'reroll', 'used': False}
            state['phase'] = 'reroll_prompt'
            return {'broadcast': True, 'prompt': {
                'id':   'reroll',
                'text': f"You rolled {total}. Radio Tower: reroll?",
            }}

        changes, transfers = _finish_roll(state, total)
        announce = _bc_announce(state, active) or _quiet_announce(changes, transfers)
        return {'broadcast': True, 'coin_changes': changes, 'transfers': transfers, 'announce': announce}

    # ── Harbor bonus response ─────────────────────────────────────────────────
    if event == 'prompt_response' and seat == active_seat and state['phase'] == 'harbor_prompt':
        rt_already_used = state['pending_prompt'].get('rt_used', False)
        base_roll = state['pending_prompt']['roll']
        final_roll = base_roll + (2 if msg.get('answer') else 0)
        state['last_roll'] = final_roll
        state['pending_prompt'] = None

        if has_landmark(active, 'radio_tower') and not rt_already_used:
            state['pending_prompt'] = {'type': 'reroll', 'used': False}
            state['phase'] = 'reroll_prompt'
            return {'broadcast': True, 'prompt': {
                'id':   'reroll',
                'text': f"Final roll: {final_roll}. Radio Tower: reroll?",
            }}

        changes, transfers = _finish_roll(state, final_roll)
        announce = _bc_announce(state, active) or _quiet_announce(changes, transfers)
        return {'broadcast': True, 'coin_changes': changes, 'transfers': transfers, 'announce': announce}

    # ── Radio Tower response ───────────────────────────────────────────────────
    if event == 'prompt_response' and seat == active_seat and state['phase'] == 'reroll_prompt':
        if msg.get('answer'):
            dice = [roll_die() for _ in range(len(state['last_dice']))]
            total = sum(dice)
            doubles = (len(dice) == 2 and dice[0] == dice[1])
            state['last_dice']  = dice
            state['last_roll']  = total
            state['doubles']    = doubles
            state['ap_active']  = doubles and has_landmark(active, 'amusement_park')
            add_log(state, f"{active['name']} rerolls → {total}")

            # Harbor bonus check on the fresh reroll — Radio Tower already spent
            if total >= 10 and has_landmark(active, 'harbor'):
                state['pending_prompt'] = {'type': 'harbor_bonus', 'roll': total, 'rt_used': True}
                state['phase'] = 'harbor_prompt'
                return {'broadcast': True, 'prompt': {
                    'id':   'harbor_bonus',
                    'text': f"Rerolled {total}. Harbor: add +2 to make it {total + 2}?",
                }}

        state['pending_prompt'] = None
        changes, transfers = _finish_roll(state, state['last_roll'])
        announce = _bc_announce(state, active) or _quiet_announce(changes, transfers)
        return {'broadcast': True, 'coin_changes': changes, 'transfers': transfers, 'announce': announce}

    # ── Tuna Boat interactive roll ────────────────────────────────────────────
    if event == 'tuna_roll' and seat == active_seat and state['phase'] == 'tuna_roll':
        dice = [roll_die(), roll_die()]
        tuna_total = sum(dice)
        tuna_changes = {}
        tuna_seats = state.get('pending_prompt', {}).get('tuna_seats', [])

        for p in state['players']:
            if p['seat'] not in tuna_seats:
                continue
            count = card_count(p, 'tuna_boat')
            amt = count * tuna_total
            give_coins(p, amt)
            add_log(state, f"{p['name']} gets {amt}🪙 from Tuna Boat ({dice[0]}+{dice[1]}={tuna_total})")
            tuna_changes[p['seat']] = [f"+{amt} Tuna Boat ({dice[0]}+{dice[1]}={tuna_total})"]

        state['phase'] = 'build'
        state['pending_prompt'] = None
        return {'broadcast': True, 'coin_changes': tuna_changes}

    # ── TV Station target pick ────────────────────────────────────────────────
    if event == 'tv_station_pick' and seat == active_seat and state['phase'] == 'tv_station':
        target_seat = msg.get('target_seat')
        if target_seat is None:
            return {}
        target = player_by_seat(state, int(target_seat))
        if not target or target['seat'] == active_seat:
            return {}
        taken = take_coins(target, active, 5)
        tv_transfers = []
        tv_changes   = {}
        if taken:
            add_log(state, f"{active['name']} takes {taken}🪙 from {target['name']} (TV Station)")
            tv_transfers.append(f"{target['name']} pays {taken}🪙 to {active['name']} (TV Station)")
            tv_changes[active_seat]       = [f"+{taken} TV Station"]
            tv_changes[target['seat']]    = [f"-{taken} TV Station"]
        _set_interactive_phase(state, state['last_roll'], tv_done=True)
        announce = _bc_announce(state, active)
        return {'broadcast': True, 'coin_changes': tv_changes, 'transfers': tv_transfers, 'announce': announce}

    # ── Business Center trade ─────────────────────────────────────────────────
    if event == 'business_center' and seat == active_seat and state['phase'] == 'business_center':
        my_card  = msg.get('my_card')
        opp_seat = msg.get('opp_seat')
        opp_card = msg.get('opp_card')
        if my_card is None or opp_seat is None or opp_card is None:
            return {}
        opp = player_by_seat(state, int(opp_seat))
        if not opp:
            return {}
        my_def  = CARD_DEFS.get(my_card)
        opp_def = CARD_DEFS.get(opp_card)
        if not (my_def and opp_def):
            return {}
        if my_def['type'] == 'Purple Major' or opp_def['type'] == 'Purple Major':
            return {}
        if card_count(active, my_card) < 1 or card_count(opp, opp_card) < 1:
            return {}

        active['cards'][my_card] -= 1
        if active['cards'][my_card] == 0:
            del active['cards'][my_card]
        active['cards'][opp_card] = active['cards'].get(opp_card, 0) + 1

        opp['cards'][opp_card] -= 1
        if opp['cards'][opp_card] == 0:
            del opp['cards'][opp_card]
        opp['cards'][my_card] = opp['cards'].get(my_card, 0) + 1

        add_log(state, f"{active['name']} traded {my_def['name']} ↔ {opp['name']}'s {opp_def['name']}")
        state['phase'] = 'build'
        state['pending_prompt'] = None
        return {'broadcast': True,
                'announce': f"🔄 {active['name']} swapped {my_def['name']} for {opp['name']}'s {opp_def['name']}"}

    # ── Skip Business Center ──────────────────────────────────────────────────
    if event == 'skip_business_center' and seat == active_seat and state['phase'] == 'business_center':
        state['phase'] = 'build'
        state['pending_prompt'] = None
        return {'broadcast': True}

    # ── Cleaning Company type pick (Sharp Phase B) ────────────────────────────
    if event == 'cleaning_company_pick' and seat == active_seat and state['phase'] == 'cleaning_company':
        card_type = msg.get('card_type')
        card = CARD_DEFS.get(card_type)
        # Validate server-side: must be a real, non-Major type with an open copy
        # somewhere on the board (the only legal targets).
        if not card or card['type'] == 'Purple Major':
            return {}
        if card_type not in _cleaning_targets(state):
            return {}

        closed_total = 0
        for p in state['players']:
            newly = active_copies(p, card_type)   # only currently-open copies close
            if newly > 0:
                close_for_renovation(p, card_type, newly)
                closed_total += newly

        clean_changes = {}
        if closed_total:
            give_coins(active, closed_total)   # 1 coin per copy closed, from the bank
            add_log(state, f"{active['name']} closes {closed_total}× {card['name']} "
                           f"for renovation (+{closed_total}🪙 Cleaning Company)")
            clean_changes[active_seat] = [f"+{closed_total} Cleaning Company"]

        state['pending_prompt'] = None
        _set_interactive_phase(state, state['last_roll'], cleaning_done=True)
        return {'broadcast': True, 'coin_changes': clean_changes}

    # ── Tech Startup invest (Sharp C1) ────────────────────────────────────────
    # Optional, on your turn, during your build window: move 1 coin onto the card.
    # At most once per turn (tech_invest_used); the total persists across turns.
    if event == 'tech_startup_invest' and seat == active_seat and state['phase'] == 'build':
        if card_count(active, 'tech_startup') < 1:
            return {}
        if state.get('tech_invest_used'):
            return {}
        if active['coins'] < 1:
            return {}
        active['coins'] -= 1
        inv = active.setdefault('investments', {})
        inv['tech_startup'] = inv.get('tech_startup', 0) + 1
        state['tech_invest_used'] = True
        add_log(state, f"{active['name']} invests 1🪙 in Tech Startup (total {inv['tech_startup']}🪙)")
        return {'broadcast': True, 'coin_changes': {active_seat: ['-1 Tech Startup (invest)']}}

    # ── Demolition Company landmark pick (Sharp C2) ───────────────────────────
    if event == 'demolition_pick' and seat == active_seat and state['phase'] == 'demolition':
        lm_id = msg.get('landmark_id')
        # Validate server-side: must be the active player's built, non-City-Hall lm.
        if lm_id not in _demolishable_landmarks(active):
            return {}
        _demolish(state, active, lm_id)
        remaining = state['pending_prompt'].get('remaining', 1) - 1
        state['pending_prompt'] = None
        if not _resume_demolition(state, remaining):
            return {'broadcast': True}              # another demolition prompt is set
        _set_interactive_phase(state, state['last_roll'], demolition_done=True)
        return {'broadcast': True}

    # ── Moving Company give pick (Sharp C2) ───────────────────────────────────
    if event == 'moving_company_pick' and seat == active_seat and state['phase'] == 'moving_company':
        card_id     = msg.get('card_id')
        target_seat = msg.get('target_seat')
        card = CARD_DEFS.get(card_id)
        # Validate: a real non-Major card the active player owns, given to a real
        # other player. (Moving Company itself is non-Major, so it's giveable.)
        if not card or card['type'] == 'Purple Major' or card_count(active, card_id) < 1:
            return {}
        if target_seat is None:
            return {}
        target = player_by_seat(state, int(target_seat))
        if not target or target['seat'] == active_seat:
            return {}

        _remove_card(active, card_id)
        _add_card(target, card_id)
        give_coins(active, 4)
        add_log(state, f"{active['name']} gives {card['name']} to {target['name']} (+4🪙 Moving Company)")
        remaining = state['pending_prompt'].get('remaining', 1) - 1
        state['pending_prompt'] = None
        if not _resume_moving(state, remaining):
            return {'broadcast': True, 'coin_changes': {active_seat: ['+4 Moving Company']}}
        _set_interactive_phase(state, state['last_roll'], moving_done=True)
        return {'broadcast': True, 'coin_changes': {active_seat: ['+4 Moving Company']}}

    # ── Build ─────────────────────────────────────────────────────────────────
    if event == 'build' and seat == active_seat and state['phase'] == 'build':
        build_type = msg.get('type')
        item_id    = msg.get('id')

        if build_type == 'card':
            card = CARD_DEFS.get(item_id)
            if not card:
                return {}
            if active['coins'] < card['cost']:
                return {}
            if state['supply'].get(item_id, 0) <= 0:
                return {}
            if card.get('max_per_player') == 1 and card_count(active, item_id) >= 1:
                return {}
            active['coins'] -= card['cost']
            active['cards'][item_id] = active['cards'].get(item_id, 0) + 1
            state['supply'][item_id] -= 1
            add_log(state, f"{active['name']} bought {card['name']}")
            if item_id == 'loan_office':
                # Sharp C1: build-time payout — take 5 from the bank immediately.
                give_coins(active, 5)
                add_log(state, f"{active['name']} gets 5🪙 (Loan Office, on build)")

        elif build_type == 'landmark':
            lm = next((l for l in active['landmarks'] if l['id'] == item_id), None)
            if not lm or lm['built'] or active['coins'] < lm['cost']:
                return {}
            active['coins'] -= lm['cost']
            lm['built'] = True
            add_log(state, f"{active['name']} built {lm['name']} 🏛️")

        if check_win(state):
            return {'broadcast': True}

        announce = _check_amusement_park(state)
        return {'broadcast': True, 'announce': announce} if announce else {'broadcast': True}

    # ── Skip build ────────────────────────────────────────────────────────────
    if event == 'skip_build' and seat == active_seat and state['phase'] == 'build':
        if has_landmark(active, 'airport'):
            give_coins(active, 10)
            add_log(state, f"{active['name']} gets 10🪙 (Airport)")
        announce = _check_amusement_park(state)
        if not announce:
            announce = f"⏭️ {active['name']} skipped building."
        return {'broadcast': True, 'announce': announce}

    return {}


# ── Internal helpers ───────────────────────────────────────────────────────────

def _bc_announce(state, active):
    """Return a broadcast announce string when Business Center phase just started, else None."""
    if state.get('phase') == 'business_center':
        return f"🔄 Business Center! {active['name']} may trade an establishment."
    return None


def _quiet_announce(changes, transfers):
    """Return a fallback announce when the roll produced no coin activity at all."""
    if not changes and not transfers:
        return "🎲 No income this roll."
    return None


def _finish_roll(state, roll):
    changes, transfers = resolve_cards(state, roll)
    _set_interactive_phase(state, roll)
    return changes, transfers


def _cleaning_targets(state):
    """Non-Major establishment types with at least one OPEN (non-renovated) copy
    anywhere on the board — the only legal Cleaning Company targets."""
    totals = {}
    for p in state['players']:
        for cid in p['cards']:
            if CARD_DEFS[cid]['type'] == 'Purple Major':
                continue
            if active_copies(p, cid) > 0:
                totals[cid] = totals.get(cid, 0) + active_copies(p, cid)
    return sorted(totals)


def _interactive_copies(state, card_id):
    """Active (pre-reopen) copies of an interactive green card this roll — stashed
    by resolve_cards so renovated copies don't over-fire (see Demolition/Moving)."""
    return state.get('interactive_active_copies', {}).get(card_id, 0)


# ── Demolition Company (Sharp C2) — landmark loss ────────────────────────────

def _demolishable_landmarks(player):
    """Built landmarks the player may demolish — City Hall can never be demolished."""
    return [lm['id'] for lm in player['landmarks']
            if lm['built'] and lm['id'] != 'city_hall']

def _demolish(state, player, lm_id):
    """Demolish one built, non-City-Hall landmark and pay 8. No-op (no pay) if the
    landmark isn't a valid target."""
    for lm in player['landmarks']:
        if lm['id'] == lm_id and lm['built'] and lm['id'] != 'city_hall':
            lm['built'] = False
            give_coins(player, 8)
            add_log(state, f"{player['name']} demolishes {lm['name']} (+8🪙 Demolition Company)")
            return True
    return False

def _resume_demolition(state, remaining):
    """Demolish `remaining` landmarks: auto-resolve while there's no real choice
    (exactly one demolishable landmark), prompt when the player must choose. Returns
    True when fully resolved, False when paused for a demolition_pick."""
    active = player_by_seat(state, state['active_seat'])
    while remaining > 0:
        demolishable = _demolishable_landmarks(active)
        if not demolishable:
            break                                   # nothing left → stop (pay only per actual)
        if len(demolishable) == 1:
            _demolish(state, active, demolishable[0])   # no choice → auto-resolve
            remaining -= 1
            continue
        state['phase'] = 'demolition'
        state['pending_prompt'] = {'type': 'demolition', 'remaining': remaining,
                                   'targets': list(demolishable)}
        return False
    return True


# ── Moving Company (Sharp C2) — give a non-Major card for +4 ──────────────────

def _moving_targets(player):
    """Non-Major establishment types the player owns (any owned copy is giveable)."""
    return sorted(cid for cid in player['cards']
                  if card_count(player, cid) > 0 and CARD_DEFS[cid]['type'] != 'Purple Major')

def _remove_card(player, card_id):
    """Remove one copy of card_id, clamping its renovation count to what remains."""
    n = player['cards'].get(card_id, 0)
    if n <= 1:
        player['cards'].pop(card_id, None)
    else:
        player['cards'][card_id] = n - 1
    reno = player.get('renovation', {})
    if card_id in reno:
        left = player['cards'].get(card_id, 0)
        if reno[card_id] > left:
            reno[card_id] = left
        if reno[card_id] <= 0:
            reno.pop(card_id, None)

def _add_card(player, card_id):
    player['cards'][card_id] = player['cards'].get(card_id, 0) + 1

def _resume_moving(state, remaining):
    """Prompt for the next give while the active player still has a giveable card
    and another player to give to. Returns True when fully resolved, False when
    paused for a moving_company_pick."""
    active = player_by_seat(state, state['active_seat'])
    others = [p for p in state['players'] if p['seat'] != active['seat']]
    while remaining > 0:
        if not _moving_targets(active) or not others:
            break
        state['phase'] = 'moving_company'
        state['pending_prompt'] = {'type': 'moving_company', 'remaining': remaining,
                                   'giveable': _moving_targets(active),
                                   'targets': [p['seat'] for p in others]}
        return False
    return True


def _set_interactive_phase(state, roll, tv_done=False, cleaning_done=False,
                           demolition_done=False, moving_done=False):
    """Advance to the next interactive phase:
    TV Station → Cleaning Company → Business Center → Demolition → Moving → Tuna → Build."""
    active = player_by_seat(state, state['active_seat'])

    # TV Station — player chooses target
    if not tv_done and card_count(active, 'tv_station') > 0 and roll in CARD_DEFS['tv_station']['dice']:
        opps = [p for p in state['players'] if p['seat'] != state['active_seat']]
        if opps:
            state['phase'] = 'tv_station'
            state['pending_prompt'] = {'type': 'tv_station'}
            return

    # Cleaning Company — player chooses a non-Major type to close board-wide
    if (not cleaning_done and card_count(active, 'cleaning_company') > 0
            and roll in CARD_DEFS['cleaning_company']['dice']):
        targets = _cleaning_targets(state)
        if targets:
            state['phase'] = 'cleaning_company'
            state['pending_prompt'] = {'type': 'cleaning_company', 'targets': targets}
            return

    # Business Center — player chooses trade
    if card_count(active, 'business_center') > 0 and roll in CARD_DEFS['business_center']['dice']:
        opp_has = any(
            any(CARD_DEFS.get(c, {}).get('type') != 'Purple Major' for c in opp['cards'])
            for opp in state['players'] if opp['seat'] != state['active_seat']
        )
        mine_has = any(
            CARD_DEFS.get(c, {}).get('type') != 'Purple Major' for c in active['cards']
        )
        if opp_has and mine_has:
            state['phase'] = 'business_center'
            state['pending_prompt'] = {'type': 'business_center'}
            return

    # Demolition Company — active demolishes their own constructed landmark(s).
    # Mandatory when a demolishable landmark exists (you only choose which); with
    # no demolishable landmark the card does nothing (no +8).
    if not demolition_done and roll in CARD_DEFS['demolition_company']['dice']:
        remaining = min(_interactive_copies(state, 'demolition_company'),
                        len(_demolishable_landmarks(active)))
        if remaining > 0 and not _resume_demolition(state, remaining):
            return                                  # paused for a demolition_pick

    # Moving Company — active gives a non-Major card to another player for +4.
    if not moving_done and roll in CARD_DEFS['moving_company']['dice']:
        remaining = _interactive_copies(state, 'moving_company')
        if remaining > 0 and not _resume_moving(state, remaining):
            return                                  # paused for a moving_company_pick

    # Tuna Boat
    tuna_players = [
        p for p in state['players']
        if card_count(p, 'tuna_boat') > 0
        and has_landmark(p, 'harbor')
        and roll in CARD_DEFS['tuna_boat']['dice']
    ]
    if tuna_players:
        names = ', '.join(p['name'] for p in tuna_players)
        add_log(state, f"🐟 Tuna Boat! {names} — roll 2 dice to collect!")
        state['phase'] = 'tuna_roll'
        state['pending_prompt'] = {
            'type': 'tuna_roll',
            'tuna_seats': [p['seat'] for p in tuna_players],
        }
        return

    state['phase'] = 'build'
    state['pending_prompt'] = None

def _check_amusement_park(state):
    if state.get('ap_active') and not state['ap_used']:
        active = player_by_seat(state, state['active_seat'])
        msg = f"🎡 Amusement Park! {active['name']} rolled doubles and gets another turn!"
        add_log(state, msg)
        state['ap_active']      = False
        state['ap_used']        = True
        state['phase']          = 'roll'
        state['last_roll']      = None
        state['last_dice']      = []
        state['tech_invest_used'] = False   # a fresh turn → invest allowance resets
        state['pending_prompt'] = None
        return msg
    advance_turn(state)
    return None
