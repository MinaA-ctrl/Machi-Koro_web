/**
 * Game-state types — mirror the authoritative dict built by
 * machi_koro_engine.create_initial_state (game_engine.py). The server is the
 * source of truth; the frontend only renders/animates over a `state_update`
 * snapshot and never mutates these locally.
 */

export type CardSymbol =
  | 'wheat'
  | 'cow'
  | 'gear'
  | 'bread'
  | 'cup'
  | 'factory'
  | 'fruit'
  | 'fish'
  | 'tower'
  | 'grape'
  | 'grain'
  | 'store'
  | 'restaurant'
  | 'loan'

export type CardType =
  | 'Blue Primary'
  | 'Green Secondary'
  | 'Red Restaurant'
  | 'Purple Major'

export interface CardDef {
  id: string
  name: string
  dice: number[]
  type: CardType
  cost: number
  symbol: CardSymbol
  effect: string
  max_per_player?: number
  requires_landmark?: string
}

export interface Landmark {
  id: string
  name: string
  cost: number
  built: boolean
  effect: string
}

export interface Player {
  seat: number
  name: string
  user_id: number | null
  coins: number
  /** card_id -> owned count */
  cards: Record<string, number>
  /** card_id -> closed copies awaiting renovation (Sharp Phase B) */
  renovation: Record<string, number>
  /** card_id -> invested coins (Sharp Tech Startup) */
  investments: Record<string, number>
  landmarks: Landmark[]
}

export type GamePhase = 'roll' | 'build' | 'finished' | string

export interface PendingPrompt {
  id: string
  text: string
  [k: string]: unknown
}

export interface GameState {
  phase: GamePhase
  version: string
  active_seat: number
  last_roll: number | null
  last_dice: number[]
  doubles: boolean
  ap_active: boolean
  ap_used: boolean
  tech_invest_used: boolean
  interactive_active_copies: Record<string, unknown>
  pending_prompt: PendingPrompt | null
  players: Player[]
  /** Face-up market card defs (10 distinct in Variable Supply, all in classic). */
  market: CardDef[]
  /** card_id -> remaining copies in supply. */
  supply: Record<string, number>
  card_defs: Record<string, CardDef>
  winner: number | null
  game_seq: number
  /** English log lines (legacy). The localized log renders from `events`. */
  log: string[]
  /** Bounded keyed-event buffer (last ~60) — the translatable log/animation source. */
  events?: KeyedEvent[]
  event_seq?: number
  /** Variable Supply only: the face-down draw pile. Presence signals VS is active. */
  deck?: string[]
  scores?: Record<string, number> | unknown
}

// ── Interactive prompts (game_prompt) — machi_koro_engine.build_prompt_payload ──
// Discriminated on `type`. params/options shapes are pinned to the engine builder.

interface PromptBase {
  promptId: string
  active_seat: number
  response_event: string | null
  /** The move the server auto-applies on timeout — a guaranteed-valid action. */
  default: Record<string, unknown> | null
  timeout_seconds: number
  /** English fallback; the UI localizes from `type` + `params`. */
  text: string
}
export interface YesNoPrompt extends PromptBase {
  type: 'harbor_bonus' | 'reroll'
  params: { roll: number; total_with_bonus?: number }
  options: { value: boolean }[]
}
export interface TvStationPrompt extends PromptBase {
  type: 'tv_station'
  params: { opponents: { seat: number; name: string; coins: number }[] }
  options: { target_seat: number }[]
}
export interface CleaningPrompt extends PromptBase {
  type: 'cleaning_company'
  params: { targets: string[] }
  options: { card_type: string }[]
}
export interface DemolitionPrompt extends PromptBase {
  type: 'demolition'
  params: { targets: string[]; remaining: number }
  options: { landmark_id: string }[]
}
export interface MovingPrompt extends PromptBase {
  type: 'moving_company'
  params: { giveable: string[]; targets: number[]; remaining: number }
  options: { cards: string[]; target_seats: number[] }
}
export interface BusinessCenterPrompt extends PromptBase {
  type: 'business_center'
  params: {
    my_cards: string[]
    opponents: { seat: number; name: string; cards: string[] }[]
  }
}
export interface TunaPrompt extends PromptBase {
  type: 'tuna_roll'
  params: { tuna_seats: number[] }
}

export type GamePrompt =
  | YesNoPrompt
  | TvStationPrompt
  | CleaningPrompt
  | DemolitionPrompt
  | MovingPrompt
  | BusinessCenterPrompt
  | TunaPrompt

export interface GamePromptEvent {
  event: 'game_prompt'
  promptId: string
  type: GamePrompt['type']
  [k: string]: unknown
}

/** Ordered keyed-event delta for granular animation (dice, payouts, market reveal). */
export interface KeyedEvent {
  seq: number
  t: string
  [k: string]: unknown
}
export interface GameEventsEvent {
  event: 'game_events'
  events: KeyedEvent[]
}

// ── WebSocket event envelopes (from websocket-server/app/ws.py) ──────────────

export interface StateUpdateEvent {
  event: 'state_update'
  state: GameState
  connected_count: number
}
export interface GameToastEvent {
  event: 'game_toast'
  text: string
}
export interface CoinEvent {
  event: 'coin_event'
  changes: number[]
}
export interface PromptEvent {
  event: 'prompt'
  text: string
  promptId: string
}
export interface ReactionEvent {
  event: 'reaction'
  seat: number
  emoji: string
}
export interface PlayerLeftGameEvent {
  event: 'player_left_game'
  name: string
  seat: number
}
export interface PlayerRejoinedGameEvent {
  event: 'player_rejoined_game'
  name: string
  seat: number
}

export type GameWsEvent =
  | StateUpdateEvent
  | GameToastEvent
  | CoinEvent
  | PromptEvent
  | GamePromptEvent
  | GameEventsEvent
  | ReactionEvent
  | PlayerLeftGameEvent
  | PlayerRejoinedGameEvent

// ── Lobby WS events (from lobby_ws) ──────────────────────────────────────────
export interface LobbyPlayerJoinedEvent {
  event: 'player_joined'
  seat: string
}
export interface LobbyPlayerLeftEvent {
  event: 'player_left'
  seat: string
}
export interface LobbyPlayerKickedEvent {
  event: 'player_kicked'
  seat: string
}
export interface LobbyTableClosedEvent {
  event: 'table_closed'
}

export type LobbyWsEvent =
  | LobbyPlayerJoinedEvent
  | LobbyPlayerLeftEvent
  | LobbyPlayerKickedEvent
  | LobbyTableClosedEvent
  | { event: string; [k: string]: unknown }
