import type { CardDef, GamePrompt, GameState } from '@/types/game'

/**
 * A canned mid-game Basic state for the dev `board-preview` route — lets us render
 * and screenshot the board's visual design without a running backend. NOT used in
 * production. Shapes match machi_koro_engine's state exactly.
 */
const DEFS: Record<string, CardDef> = {
  wheat_field: { id: 'wheat_field', name: 'Wheat Field', dice: [1], type: 'Blue Primary', cost: 1, symbol: 'wheat', effect: 'Get 1 coin from the bank.' },
  ranch: { id: 'ranch', name: 'Ranch', dice: [2], type: 'Blue Primary', cost: 1, symbol: 'cow', effect: 'Get 1 coin from the bank.' },
  forest: { id: 'forest', name: 'Forest', dice: [5], type: 'Blue Primary', cost: 3, symbol: 'gear', effect: 'Get 1 coin from the bank.' },
  mine: { id: 'mine', name: 'Mine', dice: [9], type: 'Blue Primary', cost: 6, symbol: 'gear', effect: 'Get 5 coins from the bank.' },
  apple_orchard: { id: 'apple_orchard', name: 'Apple Orchard', dice: [10], type: 'Blue Primary', cost: 3, symbol: 'wheat', effect: 'Get 3 coins from the bank.' },
  bakery: { id: 'bakery', name: 'Bakery', dice: [2, 3], type: 'Green Secondary', cost: 1, symbol: 'bread', effect: 'Get 1 coin from the bank.' },
  convenience_store: { id: 'convenience_store', name: 'Convenience Store', dice: [4], type: 'Green Secondary', cost: 2, symbol: 'bread', effect: 'Get 3 coins from the bank.' },
  cheese_factory: { id: 'cheese_factory', name: 'Cheese Factory', dice: [7], type: 'Green Secondary', cost: 5, symbol: 'factory', effect: 'Get 3 coins per Ranch you own.' },
  furniture_factory: { id: 'furniture_factory', name: 'Furniture Factory', dice: [8], type: 'Green Secondary', cost: 3, symbol: 'factory', effect: 'Get 3 coins per Forest/Mine you own.' },
  cafe: { id: 'cafe', name: 'Café', dice: [3], type: 'Red Restaurant', cost: 2, symbol: 'cup', effect: 'Take 1 coin from the active player.' },
  family_restaurant: { id: 'family_restaurant', name: 'Family Restaurant', dice: [9, 10], type: 'Red Restaurant', cost: 3, symbol: 'cup', effect: 'Take 2 coins from the active player.' },
  stadium: { id: 'stadium', name: 'Stadium', dice: [6], type: 'Purple Major', cost: 6, symbol: 'tower', effect: 'Take 2 coins from each opponent.', max_per_player: 1 },
  tv_station: { id: 'tv_station', name: 'TV Station', dice: [6], type: 'Purple Major', cost: 7, symbol: 'tower', effect: 'Take 5 coins from any one opponent.', max_per_player: 1 },
  business_center: { id: 'business_center', name: 'Business Center', dice: [6], type: 'Purple Major', cost: 8, symbol: 'tower', effect: 'Trade an establishment with an opponent.', max_per_player: 1 },
}

const MARKET_IDS = [
  'wheat_field', 'ranch', 'forest', 'mine', 'apple_orchard',
  'bakery', 'convenience_store', 'cheese_factory', 'furniture_factory',
  'cafe', 'family_restaurant', 'stadium', 'tv_station', 'business_center',
]

const LANDMARKS = (built: string[]) => [
  { id: 'train_station', name: 'Train Station', cost: 4, effect: 'Roll 2 dice.', built: built.includes('train_station') },
  { id: 'shopping_mall', name: 'Shopping Mall', cost: 10, effect: '+1 coin per ☕/🍞 card.', built: built.includes('shopping_mall') },
  { id: 'amusement_park', name: 'Amusement Park', cost: 16, effect: 'Doubles → extra turn.', built: built.includes('amusement_park') },
  { id: 'radio_tower', name: 'Radio Tower', cost: 22, effect: 'Reroll once per turn.', built: built.includes('radio_tower') },
]

export const BOARD_FIXTURE: GameState = {
  phase: 'build',
  version: 'basic',
  active_seat: 0,
  last_roll: 7,
  last_dice: [3, 4],
  doubles: false,
  ap_active: false,
  ap_used: false,
  tech_invest_used: false,
  interactive_active_copies: {},
  pending_prompt: null,
  winner: null,
  game_seq: 0,
  card_defs: DEFS,
  market: MARKET_IDS.map((id) => DEFS[id]!),
  supply: Object.fromEntries(MARKET_IDS.map((id) => [id, id === 'tv_station' ? 0 : id === 'stadium' ? 2 : 6])),
  players: [
    {
      seat: 0, name: 'You', user_id: null, coins: 14,
      cards: { wheat_field: 3, bakery: 2, ranch: 1, cafe: 1, convenience_store: 1, forest: 1 },
      renovation: {}, investments: {},
      landmarks: LANDMARKS(['train_station']),
    },
    {
      seat: 1, name: 'Akira', user_id: null, coins: 8,
      cards: { wheat_field: 1, bakery: 1, ranch: 2, cheese_factory: 1 },
      renovation: {}, investments: {},
      landmarks: LANDMARKS([]),
    },
    {
      seat: 2, name: 'Mei', user_id: null, coins: 21,
      cards: { wheat_field: 2, bakery: 1, forest: 2, mine: 1 },
      renovation: {}, investments: {},
      landmarks: LANDMARKS(['train_station', 'shopping_mall']),
    },
  ],
  log: [
    '🎲 You rolled 7 (3 + 4).',
    '☕ Café: Akira takes 1 coin from you.',
  ],
  event_seq: 4,
  events: [
    { seq: 1, t: 'roll', name: 'You', dice_count: 2, total: 7, dice: [3, 4] },
    { seq: 2, t: 'income', name: 'Akira', amount: 3, source: 'cheese_factory' },
    { seq: 3, t: 'take', taker_name: 'Akira', payer_name: 'You', amount: 1, source: 'cafe' },
    { seq: 4, t: 'buy_card', name: 'You', card_id: 'convenience_store' },
  ],
}

/**
 * Variant with the 10-card Variable Supply active (`deck` present). Used to preview
 * the remaining-count chips and the flip-reveal. A couple of slots are low/sold so
 * the chips and reveal styling are visible.
 */
export const BOARD_FIXTURE_VS: GameState = {
  ...BOARD_FIXTURE,
  deck: ['mine', 'mine', 'forest', 'forest', 'cafe'],
  supply: {
    wheat_field: 6, ranch: 4, forest: 3, mine: 1, apple_orchard: 5,
    bakery: 6, convenience_store: 2, cheese_factory: 1, furniture_factory: 6,
    family_restaurant: 3,
  },
  market: ['wheat_field', 'ranch', 'forest', 'mine', 'apple_orchard', 'bakery', 'convenience_store', 'cheese_factory', 'furniture_factory', 'family_restaurant'].map(
    (id) => DEFS[id]!,
  ),
}

/** Canned structured prompts for previewing each Sharp/interactive overlay. */
export const PROMPT_FIXTURES: Record<string, GamePrompt> = {
  tv_station: {
    promptId: 'tv_station', type: 'tv_station', active_seat: 0, response_event: 'tv_station_pick',
    default: { event: 'tv_station_pick', target_seat: 2 }, timeout_seconds: 45, text: '',
    params: { opponents: [{ seat: 1, name: 'Akira', coins: 8 }, { seat: 2, name: 'Mei', coins: 21 }] },
    options: [{ target_seat: 1 }, { target_seat: 2 }],
  },
  cleaning_company: {
    promptId: 'cleaning_company', type: 'cleaning_company', active_seat: 0, response_event: 'cleaning_company_pick',
    default: { event: 'cleaning_company_pick', card_type: 'wheat_field' }, timeout_seconds: 45, text: '',
    params: { targets: ['wheat_field', 'ranch', 'bakery', 'forest'] },
    options: [{ card_type: 'wheat_field' }, { card_type: 'ranch' }, { card_type: 'bakery' }, { card_type: 'forest' }],
  },
  demolition: {
    promptId: 'demolition', type: 'demolition', active_seat: 0, response_event: 'demolition_pick',
    default: { event: 'demolition_pick', landmark_id: 'train_station' }, timeout_seconds: 45, text: '',
    params: { targets: ['train_station'], remaining: 1 },
    options: [{ landmark_id: 'train_station' }],
  },
  moving_company: {
    promptId: 'moving_company', type: 'moving_company', active_seat: 0, response_event: 'moving_company_pick',
    default: { event: 'moving_company_pick', card_id: 'wheat_field', target_seat: 1 }, timeout_seconds: 45, text: '',
    params: { giveable: ['wheat_field', 'bakery', 'cafe'], targets: [1, 2], remaining: 1 },
    options: { cards: ['wheat_field', 'bakery', 'cafe'], target_seats: [1, 2] },
  },
  business_center: {
    promptId: 'business_center', type: 'business_center', active_seat: 0, response_event: 'business_center',
    default: { event: 'skip_business_center' }, timeout_seconds: 45, text: '',
    params: {
      my_cards: ['wheat_field', 'bakery', 'cafe'],
      opponents: [
        { seat: 1, name: 'Akira', cards: ['ranch', 'cheese_factory'] },
        { seat: 2, name: 'Mei', cards: ['forest', 'mine'] },
      ],
    },
  },
}
