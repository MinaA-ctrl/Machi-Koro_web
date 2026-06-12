'use client'

/**
 * Per-table membership the lobby needs after navigation: which seat I hold and the
 * per-seat game-WS token returned by create/join/start. Kept in sessionStorage
 * (tab-scoped, cleared on tab close) keyed by table code — it is short-lived and
 * specific to the active table, unlike the account JWT in tokens.ts.
 */
export interface Membership {
  code: string
  seat: number
  /** Per-seat WS token from create/join, refreshed by start. */
  wsToken: string
  isHost: boolean
}

const KEY = (code: string) => `mk.member.${code.toUpperCase()}`

export function setMembership(m: Membership): void {
  if (typeof window === 'undefined') return
  window.sessionStorage.setItem(KEY(m.code), JSON.stringify(m))
}

export function getMembership(code: string): Membership | null {
  if (typeof window === 'undefined') return null
  const raw = window.sessionStorage.getItem(KEY(code))
  if (!raw) return null
  try {
    return JSON.parse(raw) as Membership
  } catch {
    return null
  }
}

export function clearMembership(code: string): void {
  if (typeof window === 'undefined') return
  window.sessionStorage.removeItem(KEY(code))
}
