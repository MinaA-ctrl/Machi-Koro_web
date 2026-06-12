"""Keyed (structured) game events — the i18n + animation source of truth.

Stage 3 (S3.4/S3.5) makes the engine emit **structured, server-authoritative
events** instead of only English log strings, so the React frontend can:
  - translate the game log + prompts (EN/RU) from a key + params, and
  - animate game moments (dice, coin movement, market reveal) over the engine's
    truth without recomputing outcomes.

Design: each event is a plain dict ``{'t': <type>, ...params}`` plus a monotonic
``seq`` stamped by the engine when it's appended. ``render_en(event)`` renders the
**exact** English string the engine used to log, so:
  - ``state['log']`` stays English strings (the live WP-JS UI is unchanged), and
  - the 182 engine tests stay green (they never assert on log text, but the live
    log is byte-identical anyway).

The frontend localizes by switching on ``event['t']`` and reading the params; it
never parses the English string. Card/landmark NAMES are localized on the
frontend from ``card_id`` / ``landmark_id`` against its own catalog — this module
resolves them to English only for ``state['log']`` and back-compat toasts.

This module is pure (stdlib + card data only) and carries no transport/DB import,
matching the rest of the engine.
"""
from .card_defs import CARD_DEFS, LANDMARK_DEFS

# ── Event-type vocabulary ─────────────────────────────────────────────────────
# Stable string keys — the frontend i18n catalog and the WS contract doc key off
# these. Add new types here; never repurpose an existing one (it's a wire contract).

# Dice
ROLL              = 'roll'                # active player rolled (1 or 2 dice)
REROLL            = 'reroll'              # Radio Tower reroll

# Coin movement (the granular payout stream — ordered by `seq`)
INCOME            = 'income'              # bank -> player  ("gets N (Source)")
TAKE              = 'take'                # player -> player ("X takes N from Y (Source)")
BANK_PAY          = 'bank_pay'            # player -> bank  ("pays N to the bank (Source)")
PARK_SPLIT        = 'park_split'          # Park pools + redistributes all coins
CITY_HALL         = 'city_hall'           # City Hall safety net (+1 at 0 coins)
TUNA_PAYOUT       = 'tuna_payout'         # Tuna Boat payout after the 2-die roll

# Renovation (Sharp B)
RENOVATION_REOPEN = 'renovation_reopen'  # a closed copy reopens (pays 0 this roll)
RENOVATION_CLOSE  = 'renovation_close'   # Winery closes itself after paying

# Interactive / Sharp resolutions
CLEANING          = 'cleaning'           # Cleaning Company closed N copies of a type
TECH_INVEST       = 'tech_invest'        # +1 coin invested onto Tech Startup
DEMOLISH          = 'demolish'           # Demolition Company razed a landmark (+8)
MOVING_GIVE       = 'moving_give'        # Moving Company gave a card away (+4)
TRADE             = 'trade'              # Business Center swap (logged form)
TUNA_ANNOUNCE     = 'tuna_announce'      # Tuna Boat is up — players must roll 2 dice

# Build
BUY_CARD          = 'buy_card'           # bought an establishment from the market
BUY_LANDMARK      = 'buy_landmark'       # constructed a landmark
LOAN_BUILD        = 'loan_build'         # Loan Office build-time +5
MARKET_REVEAL     = 'market_reveal'      # variable-supply slot diff (buy -> empty -> reveal)

# Turn / meta
AMUSEMENT_PARK    = 'amusement_park'     # doubles -> extra turn
WIN               = 'win'                # all landmarks built -> winner
WIN_FORFEIT       = 'win_forfeit'        # last player standing (others left)

# Toast-only announces (no log line in the legacy engine)
NO_INCOME         = 'no_income'          # a roll produced no coin activity
BC_OFFER          = 'bc_offer'           # Business Center: you may trade
TRADE_DONE        = 'trade_done'         # Business Center: swap completed (toast form)
SKIP_BUILD        = 'skip_build'         # active player built nothing


# ── Name resolution (English, for the derived log / legacy toasts only) ───────
# The frontend does NOT use these — it localizes from card_id / landmark_id.
_LANDMARK_NAME = {lm['id']: lm['name'] for lm in LANDMARK_DEFS}


def source_name_en(source_id):
    """English display name for a coin-source id (a card or a landmark)."""
    if source_id in CARD_DEFS:
        return CARD_DEFS[source_id]['name']
    if source_id in _LANDMARK_NAME:
        return _LANDMARK_NAME[source_id]
    return source_id


def card_name_en(card_id):
    return CARD_DEFS[card_id]['name'] if card_id in CARD_DEFS else card_id


def landmark_name_en(lm_id):
    return _LANDMARK_NAME.get(lm_id, lm_id)


# ── EN renderers ──────────────────────────────────────────────────────────────
# One renderer per event type. Each reproduces, byte-for-byte, the string the
# legacy engine produced (so state['log'] and legacy toasts are unchanged).

def _r_roll(e):
    return f"{e['name']} rolls {'🎲' * e['dice_count']} → {e['total']}"

def _r_reroll(e):
    return f"{e['name']} rerolls → {e['total']}"

def _r_income(e):
    return f"{e['name']} gets {e['amount']}🪙 ({source_name_en(e['source'])})"

def _r_take(e):
    return (f"{e['taker_name']} takes {e['amount']}🪙 from "
            f"{e['payer_name']} ({source_name_en(e['source'])})")

def _r_bank_pay(e):
    return f"{e['name']} pays {e['amount']}🪙 to the bank ({source_name_en(e['source'])})"

def _r_park_split(e):
    return f"{e['name']} pools and splits all coins equally (Park)"

def _r_city_hall(e):
    return f"{e['name']} gets 1🪙 (City Hall)"

def _r_tuna_payout(e):
    d0, d1 = e['dice']
    return (f"{e['name']} gets {e['amount']}🪙 from Tuna Boat "
            f"({d0}+{d1}={e['total']})")

def _r_renovation_reopen(e):
    return f"{e['name']}'s {card_name_en(e['card_id'])} reopens from renovation"

def _r_renovation_close(e):
    return f"{e['name']}'s {card_name_en(e['card_id'])} closes for renovation"

def _r_cleaning(e):
    return (f"{e['name']} closes {e['count']}× {card_name_en(e['card_id'])} "
            f"for renovation (+{e['count']}🪙 Cleaning Company)")

def _r_tech_invest(e):
    return f"{e['name']} invests 1🪙 in Tech Startup (total {e['total']}🪙)"

def _r_demolish(e):
    return f"{e['name']} demolishes {landmark_name_en(e['landmark_id'])} (+8🪙 Demolition Company)"

def _r_moving_give(e):
    return (f"{e['name']} gives {card_name_en(e['card_id'])} to "
            f"{e['target_name']} (+4🪙 Moving Company)")

def _r_trade(e):
    return (f"{e['name']} traded {card_name_en(e['card_id'])} ↔ "
            f"{e['opp_name']}'s {card_name_en(e['opp_card_id'])}")

def _r_tuna_announce(e):
    names = ', '.join(e['names'])
    return f"🐟 Tuna Boat! {names} — roll 2 dice to collect!"

def _r_buy_card(e):
    return f"{e['name']} bought {card_name_en(e['card_id'])}"

def _r_buy_landmark(e):
    return f"{e['name']} built {landmark_name_en(e['landmark_id'])} 🏛️"

def _r_loan_build(e):
    return f"{e['name']} gets 5🪙 (Loan Office, on build)"

def _r_amusement_park(e):
    return f"🎡 Amusement Park! {e['name']} rolled doubles and gets another turn!"

def _r_win(e):
    return f"🏆 {e['name']} wins!"

def _r_win_forfeit(e):
    return f"🏆 {e['name']} wins — all other players left!"

def _r_no_income(e):
    return "🎲 No income this roll."

def _r_bc_offer(e):
    return f"🔄 Business Center! {e['name']} may trade an establishment."

def _r_trade_done(e):
    return (f"🔄 {e['name']} swapped {card_name_en(e['card_id'])} for "
            f"{e['opp_name']}'s {card_name_en(e['opp_card_id'])}")

def _r_skip_build(e):
    return f"⏭️ {e['name']} skipped building."

def _r_market_reveal(e):
    # Events-only (no legacy log line). A neutral EN string for completeness /
    # any debug log — the frontend animates from the structured params.
    if e['revealed']:
        names = ', '.join(card_name_en(c) for c in e['revealed'])
        return f"Market: {card_name_en(e['bought_card_id'])} sold out → revealed {names}"
    return f"Market: {card_name_en(e['bought_card_id'])} sold out"


_RENDERERS = {
    ROLL: _r_roll, REROLL: _r_reroll,
    INCOME: _r_income, TAKE: _r_take, BANK_PAY: _r_bank_pay,
    PARK_SPLIT: _r_park_split, CITY_HALL: _r_city_hall, TUNA_PAYOUT: _r_tuna_payout,
    RENOVATION_REOPEN: _r_renovation_reopen, RENOVATION_CLOSE: _r_renovation_close,
    CLEANING: _r_cleaning, TECH_INVEST: _r_tech_invest,
    DEMOLISH: _r_demolish, MOVING_GIVE: _r_moving_give, TRADE: _r_trade,
    TUNA_ANNOUNCE: _r_tuna_announce,
    BUY_CARD: _r_buy_card, BUY_LANDMARK: _r_buy_landmark, LOAN_BUILD: _r_loan_build,
    MARKET_REVEAL: _r_market_reveal,
    AMUSEMENT_PARK: _r_amusement_park, WIN: _r_win, WIN_FORFEIT: _r_win_forfeit,
    NO_INCOME: _r_no_income, BC_OFFER: _r_bc_offer, TRADE_DONE: _r_trade_done,
    SKIP_BUILD: _r_skip_build,
}

# Events that historically produced NO `state['log']` line (toast-only announces
# or new animation-only events). The engine appends these to `state['events']`
# but NOT to `state['log']`, so the derived English log stays byte-identical.
TOAST_ONLY = frozenset({NO_INCOME, BC_OFFER, TRADE_DONE, SKIP_BUILD, MARKET_REVEAL})

# Coin-movement event types — the ordered "payout stream" the frontend animates
# coins over (read in `seq` order).
PAYOUT_TYPES = frozenset({INCOME, TAKE, BANK_PAY, PARK_SPLIT, CITY_HALL, TUNA_PAYOUT})


def render_en(event):
    """Render an event dict to its English string. Raises KeyError for an unknown
    type so a missing renderer is caught by tests, never shipped silently."""
    return _RENDERERS[event['t']](event)
