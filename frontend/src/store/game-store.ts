'use client'

import { create } from 'zustand'

import type { GamePrompt, GameState } from '@/types/game'

/**
 * Authoritative game state, mirrored from the server's `state_update` frames. The
 * UI is a pure view over this — it never mutates game fields locally; every action
 * round-trips through the WebSocket and comes back as a new snapshot.
 *
 * `mySeat` is the local player's seat (from table membership). Derived selectors
 * (isMyTurn etc.) are computed in components to keep the store minimal.
 */
interface GameStore {
  state: GameState | null
  connectedCount: number
  mySeat: number | null
  /** The active interactive prompt for THIS client (from `game_prompt`), or null. */
  currentPrompt: GamePrompt | null
  /** Bumped on each coin_event so a player's coin chip can pulse. */
  coinPulse: Record<number, number>

  setState: (state: GameState) => void
  setConnectedCount: (n: number) => void
  setMySeat: (seat: number | null) => void
  setPrompt: (prompt: GamePrompt | null) => void
  pulseCoins: (seats: number[]) => void
  reset: () => void
}

export const useGameStore = create<GameStore>((set) => ({
  state: null,
  connectedCount: 0,
  mySeat: null,
  currentPrompt: null,
  coinPulse: {},

  setState: (state) =>
    set((s) => {
      // Clear a stale prompt once the server reports it resolved (no pending_prompt
      // on the snapshot) so the modal can't linger after the action lands.
      const cleared = state.pending_prompt == null && s.currentPrompt != null
      return cleared ? { state, currentPrompt: null } : { state }
    }),
  setConnectedCount: (connectedCount) => set({ connectedCount }),
  setMySeat: (mySeat) => set({ mySeat }),
  setPrompt: (currentPrompt) => set({ currentPrompt }),
  pulseCoins: (seats) =>
    set((s) => {
      const next = { ...s.coinPulse }
      for (const seat of seats) next[seat] = (next[seat] ?? 0) + 1
      return { coinPulse: next }
    }),
  reset: () => set({ state: null, connectedCount: 0, coinPulse: {}, currentPrompt: null }),
}))
