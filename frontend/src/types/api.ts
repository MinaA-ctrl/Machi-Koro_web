/**
 * REST DTOs — mirror the FastAPI Pydantic models in
 * websocket-server/app/schemas.py exactly. Keep field names in lockstep with the
 * backend; this is the contract surface.
 */

export type GameVersion = 'basic' | 'harbour'

// ── auth ───────────────────────────────────────────────────────────────────
export interface TokenPair {
  access_token: string
  refresh_token: string
  token_type: string
}

export interface UserOut {
  id: number
  kind: string
  display_name: string
  email: string | null
  language: string
  avatar: string | null
}

export interface GuestReq {
  display_name?: string | null
  language?: string
}

export interface RegisterReq {
  email: string
  password: string
  display_name?: string | null
  language?: string
}

export interface LoginReq {
  email: string
  password: string
}

// ── tables ─────────────────────────────────────────────────────────────────
export interface CreateTableReq {
  name?: string | null
  is_public?: boolean
  guest_name?: string | null
  version?: GameVersion
  sharp?: boolean
  variable_supply?: boolean
  password?: string | null
}

export interface CreateTableResp {
  code: string
  seat: number
  token: string
}

export interface JoinReq {
  guest_name?: string | null
  password?: string | null
}

export interface JoinResp {
  seat: number
  token: string
}

export interface StartResp {
  started: boolean
  players: number
  token: string
}

export interface PlayerOut {
  seat: number
  display_name: string
  user_id: number | null
  is_host: boolean
}

export interface TableListItem {
  code: string
  name: string
  game_version: string
  sharp: boolean
  variable_supply: boolean
  status: string
  is_public: boolean
  player_count: number
  is_protected: boolean
}

export interface TableDetail {
  code: string
  name: string
  game_version: string
  sharp: boolean
  variable_supply: boolean
  status: string
  is_public: boolean
  created_at: string
  is_protected: boolean
  players: PlayerOut[]
}

export interface KickResp {
  kicked_seat: number
}

export interface RenameResp {
  name: string
}

/** Error envelope — FastAPI returns `{ detail: ... }`. */
export interface ApiErrorBody {
  detail?: string | { msg?: string }[] | unknown
}
