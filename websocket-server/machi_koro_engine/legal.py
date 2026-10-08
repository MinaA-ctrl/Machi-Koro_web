"""Legal-move generation — "what can this player do right now?"

`legal_actions(state, seat)` lists every message `handle_action` would accept from
`seat` in the current state, in a stable order. Bots (and the text game) pick from
this list, so they can never attempt an illegal move. Every move here is checked
against `handle_action` itself by the property tests in machi_koro_ai/tests.

Pure: reads `state`, never changes it.
"""
from .card_defs import CARD_DEFS
from .game_engine import (
    build_prompt_payload, card_count, has_landmark, player_by_seat,
)

# Phases whose moves come straight from the structured prompt payload's options.
_YES_NO_PHASES = ('harbor_prompt', 'reroll_prompt')


def legal_actions(state, seat):
    """All moves `seat` may make now (empty if it's not their decision)."""
    if state.get('phase') == 'finished' or seat != state.get('active_seat'):
        return []
    active = player_by_seat(state, seat)
    phase = state['phase']

    if phase == 'roll':
        moves = [{'event': 'roll', 'dice_count': 1}]
        if has_landmark(active, 'train_station'):
            moves.append({'event': 'roll', 'dice_count': 2})
        return moves

    if phase in _YES_NO_PHASES:
        return [{'event': 'prompt_response', 'answer': True},
                {'event': 'prompt_response', 'answer': False}]

    if phase == 'build':
        return _build_moves(state, active)

    return _prompt_moves(state, phase)


def _build_moves(state, active):
    moves = []
    coins = active['coins']
    for card_id, left in state['supply'].items():
        card = CARD_DEFS[card_id]
        if left <= 0 or card['cost'] > coins:
            continue
        if card.get('max_per_player') == 1 and card_count(active, card_id) >= 1:
            continue
        moves.append({'event': 'build', 'type': 'card', 'id': card_id})
    for lm in active['landmarks']:
        if not lm['built'] and lm['cost'] <= coins:
            moves.append({'event': 'build', 'type': 'landmark', 'id': lm['id']})
    if (card_count(active, 'tech_startup') > 0 and not state.get('tech_invest_used')
            and coins >= 1):
        moves.append({'event': 'tech_startup_invest'})
    moves.append({'event': 'skip_build'})
    return moves


def _prompt_moves(state, phase):
    payload = build_prompt_payload(state)
    if not payload:
        return []
    event = payload['response_event']
    params = payload['params']

    if phase == 'tuna_roll':
        return [{'event': 'tuna_roll'}]
    if phase == 'tv_station':
        return [{'event': event, 'target_seat': o['target_seat']} for o in payload['options']]
    if phase == 'cleaning_company':
        return [{'event': event, 'card_type': o['card_type']} for o in payload['options']]
    if phase == 'demolition':
        return [{'event': event, 'landmark_id': o['landmark_id']} for o in payload['options']]
    if phase == 'moving_company':
        return [{'event': event, 'card_id': c, 'target_seat': t}
                for c in params['giveable'] for t in params['targets']]
    if phase == 'business_center':
        moves = [{'event': 'skip_business_center'}]
        for opp in params['opponents']:
            for mine in params['my_cards']:
                for theirs in opp['cards']:
                    moves.append({'event': 'business_center', 'my_card': mine,
                                  'opp_seat': opp['seat'], 'opp_card': theirs})
        return moves
    return []
