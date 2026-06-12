'use client'

/**
 * Auth-token store. The Stage-2 backend issues a JWT access/refresh pair (guest or
 * registered). We persist them in localStorage so a refresh survives reloads; the
 * per-seat game-WS token is NOT stored here — it is short-lived and held in
 * component/store state for the active table only.
 */
import type { TokenPair } from '@/types/api'

const ACCESS_KEY = 'mk.access'
const REFRESH_KEY = 'mk.refresh'

export function getAccessToken(): string | null {
  if (typeof window === 'undefined') return null
  return window.localStorage.getItem(ACCESS_KEY)
}

export function getRefreshToken(): string | null {
  if (typeof window === 'undefined') return null
  return window.localStorage.getItem(REFRESH_KEY)
}

export function setTokens(pair: TokenPair): void {
  if (typeof window === 'undefined') return
  window.localStorage.setItem(ACCESS_KEY, pair.access_token)
  window.localStorage.setItem(REFRESH_KEY, pair.refresh_token)
}

export function clearTokens(): void {
  if (typeof window === 'undefined') return
  window.localStorage.removeItem(ACCESS_KEY)
  window.localStorage.removeItem(REFRESH_KEY)
}
