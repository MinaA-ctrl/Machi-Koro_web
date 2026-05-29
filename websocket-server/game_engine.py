import random
from copy import deepcopy
from card_defs import (
    CARD_DEFS, LANDMARK_DEFS,
    WHEAT_SYMBOL_CARDS, CUP_SYMBOL_CARDS, BREAD_SYMBOL_CARDS, GEAR_SYMBOL_CARDS,
)


# ── State creation ─────────────────────────────────────────────────────────────

def create_initial_state(players_info):
    num_players = len(players_info)
    players = []
    for p in players_info:
        players.append({
            'seat':      p['seat'],
            'name':      p['display_name'],
            'coins':     3,
            'cards':     {'wheat_field': 1, 'bakery': 1},
            'landmarks': [
                {'id': lm['id'], 'name': lm['name'], 'cost': lm['cost'],
                 'built': lm['pre_built'], 'effect': lm['effect']}
                for lm in LANDMARK_DEFS
            ],
        })

    # Supply: 6 per regular card, num_players per purple card
    supply = {}
    for card_id, card in CARD_DEFS.items():
        if card['type'] == 'Purple Major':
            supply[card_id] = num_players
        else:
            supply[card_id] = 6

    start_seat = min(p['seat'] for p in players)

    return {
        'phase':          'roll',
        'active_seat':    start_seat,
        'last_roll':      None,
        'last_dice':      [],
        'doubles':        False,
        'ap_active':      False,
        'ap_used':        False,
        'pending_prompt': None,
        'players':        players,
        'market':         list(CARD_DEFS.values()),
        'supply':         supply,
        'card_defs':      CARD_DEFS,
        'winner':         None,
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

            per_copy = {'cafe': 1, 'family_restaurant': 2, 'sushi_bar': 3,
                        'hamburger_stand': 1, 'pizza_joint': 1}.get(card_id, 1)
            amount = count * per_copy
            if has_landmark(opp, 'shopping_mall') and card['symbol'] == 'cup':
                amount += count

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

            if card_id == 'mine':
                amt = count * 5
            elif card_id == 'apple_orchard':
                amt = count * 3
            elif card_id == 'mackerel_boat':
                amt = count * 3
            else:
                amt = count  # wheat_field, ranch, forest, flower_garden

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

        mall = has_landmark(active, 'shopping_mall')
        bonus = count if (mall and card['symbol'] in ('bread', 'cup')) else 0

        if card_id == 'bakery':
            amt = count * 1 + bonus
        elif card_id == 'convenience_store':
            amt = count * 3 + bonus
        elif card_id == 'cheese_factory':
            ranches = card_count(active, 'ranch')
            amt = count * ranches * 3
        elif card_id == 'furniture_factory':
            gears = card_count(active, 'forest') + card_count(active, 'mine')
            amt = count * gears * 3
        elif card_id == 'farmers_market':
            wheat = sum(card_count(active, c) for c in WHEAT_SYMBOL_CARDS)
            amt = count * wheat * 2
        elif card_id == 'flower_shop':
            amt = count * card_count(active, 'flower_garden')
        elif card_id == 'food_warehouse':
            cups = sum(card_count(active, c) for c in CUP_SYMBOL_CARDS)
            amt = count * cups * 2
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

    # ── 5. City Hall — active player at 0 coins gets 1 ────────────────────────
    if active['coins'] == 0:
        give_coins(active, 1)
        add_log(state, f"{active['name']} gets 1🪙 (City Hall)")
        gain(active, 1, 'City Hall')

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
    state['pending_prompt'] = None


def calculate_scores(state):
    rows = []
    for p in state['players']:
        built = sum(1 for lm in p['landmarks'] if lm['built'] and lm['id'] != 'city_hall')
        rows.append({'seat': p['seat'], 'name': p['name'],
                     'landmarks_built': built, 'is_winner': p['seat'] == state.get('winner')})
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
        dice = [random.randint(1, 6) for _ in range(dice_count)]
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
            dice = [random.randint(1, 6) for _ in range(len(state['last_dice']))]
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
        dice = [random.randint(1, 6), random.randint(1, 6)]
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


def _set_interactive_phase(state, roll, tv_done=False):
    """Advance to the next interactive phase: TV Station → Business Center → Tuna → Build."""
    active = player_by_seat(state, state['active_seat'])

    # TV Station — player chooses target
    if not tv_done and card_count(active, 'tv_station') > 0 and roll in CARD_DEFS['tv_station']['dice']:
        opps = [p for p in state['players'] if p['seat'] != state['active_seat']]
        if opps:
            state['phase'] = 'tv_station'
            state['pending_prompt'] = {'type': 'tv_station'}
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
        state['pending_prompt'] = None
        return msg
    advance_turn(state)
    return None
