'use client'

/**
 * REST client for the Stage-2 FastAPI backend.
 *
 * - Bearer auth from the token store; on a 401 it transparently refreshes once
 *   using the refresh token, then retries the original request.
 * - Errors surface as `ApiError` carrying the HTTP status + the backend's
 *   `{ detail }` message so UI can show the real reason (wrong password, full
 *   table, etc.) and toasts can localize generic failures.
 */
import type {
  ApiErrorBody,
  CreateTableReq,
  CreateTableResp,
  GuestReq,
  JoinReq,
  JoinResp,
  KickResp,
  LoginReq,
  RegisterReq,
  RenameResp,
  StartResp,
  TableDetail,
  TableListItem,
  TokenPair,
  UserOut,
} from '@/types/api'
import {
  clearTokens,
  getAccessToken,
  getRefreshToken,
  setTokens,
} from './tokens'

const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? 'http://localhost:8000'

export class ApiError extends Error {
  status: number
  detail: unknown
  constructor(status: number, detail: unknown, message: string) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.detail = detail
  }
}

function detailToMessage(body: ApiErrorBody | null, fallback: string): string {
  if (!body || body.detail == null) return fallback
  if (typeof body.detail === 'string') return body.detail
  if (Array.isArray(body.detail)) {
    const first = body.detail[0]
    if (first && typeof first === 'object' && 'msg' in first) {
      return String((first as { msg?: string }).msg ?? fallback)
    }
  }
  return fallback
}

interface RequestOpts {
  method?: string
  body?: unknown
  auth?: boolean
  /** Internal — prevents an infinite refresh loop. */
  _retried?: boolean
}

async function request<T>(path: string, opts: RequestOpts = {}): Promise<T> {
  const { method = 'GET', body, auth = true, _retried = false } = opts

  const headers: Record<string, string> = { 'Content-Type': 'application/json' }
  if (auth) {
    const token = getAccessToken()
    if (token) headers.Authorization = `Bearer ${token}`
  }

  const res = await fetch(`${API_BASE}${path}`, {
    method,
    headers,
    body: body === undefined ? undefined : JSON.stringify(body),
  })

  // Transparent single refresh-and-retry on auth expiry.
  if (res.status === 401 && auth && !_retried) {
    const refreshed = await tryRefresh()
    if (refreshed) {
      return request<T>(path, { ...opts, _retried: true })
    }
    clearTokens()
  }

  if (!res.ok) {
    let parsed: ApiErrorBody | null = null
    try {
      parsed = (await res.json()) as ApiErrorBody
    } catch {
      /* non-JSON error body */
    }
    throw new ApiError(res.status, parsed?.detail, detailToMessage(parsed, res.statusText))
  }

  if (res.status === 204) return undefined as T
  return (await res.json()) as T
}

async function tryRefresh(): Promise<boolean> {
  const refresh_token = getRefreshToken()
  if (!refresh_token) return false
  try {
    const res = await fetch(`${API_BASE}/auth/refresh`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ refresh_token }),
    })
    if (!res.ok) return false
    setTokens((await res.json()) as TokenPair)
    return true
  } catch {
    return false
  }
}

// ── auth ─────────────────────────────────────────────────────────────────────
export const api = {
  async guest(req: GuestReq): Promise<TokenPair> {
    const pair = await request<TokenPair>('/auth/guest', {
      method: 'POST',
      body: req,
      auth: false,
    })
    setTokens(pair)
    return pair
  },

  async register(req: RegisterReq): Promise<TokenPair> {
    const pair = await request<TokenPair>('/auth/register', {
      method: 'POST',
      body: req,
      auth: false,
    })
    setTokens(pair)
    return pair
  },

  async login(req: LoginReq): Promise<TokenPair> {
    const pair = await request<TokenPair>('/auth/login', {
      method: 'POST',
      body: req,
      auth: false,
    })
    setTokens(pair)
    return pair
  },

  me(): Promise<UserOut> {
    return request<UserOut>('/auth/me')
  },

  // ── tables ──────────────────────────────────────────────────────────────
  createTable(req: CreateTableReq): Promise<CreateTableResp> {
    return request<CreateTableResp>('/tables', { method: 'POST', body: req })
  },

  joinTable(code: string, req: JoinReq): Promise<JoinResp> {
    return request<JoinResp>(`/tables/${code}/join`, { method: 'POST', body: req })
  },

  startTable(code: string): Promise<StartResp> {
    return request<StartResp>(`/tables/${code}/start`, { method: 'POST' })
  },

  listTables(): Promise<TableListItem[]> {
    return request<TableListItem[]>('/tables')
  },

  getTable(code: string): Promise<TableDetail> {
    return request<TableDetail>(`/tables/${code}`)
  },

  kick(code: string, seat: number): Promise<KickResp> {
    return request<KickResp>(`/tables/${code}/kick`, { method: 'POST', body: { seat } })
  },

  rename(code: string, seat: number, name: string): Promise<RenameResp> {
    return request<RenameResp>(`/tables/${code}/rename`, {
      method: 'POST',
      body: { seat, name },
    })
  },
}

export { API_BASE }
