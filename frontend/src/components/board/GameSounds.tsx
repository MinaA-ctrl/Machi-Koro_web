'use client'

import { useEffect, useRef } from 'react'

import { playSound } from '@/lib/sound'
import type { SoundName } from '@/lib/sound'
import { useGameStore } from '@/store/game-store'
import type { KeyedEvent } from '@/types/game'

/**
 * Plays sound effects off the authoritative keyed-event stream (and turn changes).
 * Renders nothing. Mirrors CoinGainNotifier's bookkeeping: tracks the last event
 * `seq` so each batch fires once, and primes on the first snapshot so a reconnect
 * doesn't replay a flurry of sounds. Coin gains/losses, buys and the turn chime are
 * scoped to THIS seat; the dice rattle plays for every roll (the table's rhythm)
 * and the victory jingle plays for everyone.
 */
export function GameSounds({ seat }: { seat: number }) {
  const events = useGameStore((s) => s.state?.events)
  const activeSeat = useGameStore((s) => s.state?.active_seat)
  const lastSeq = useRef<number | null>(null)
  const prevActive = useRef<number | null>(null)

  useEffect(() => {
    if (!events || events.length === 0) return
    const maxSeq = events[events.length - 1]!.seq
    if (lastSeq.current === null) {
      lastSeq.current = maxSeq
      return
    }
    const want = new Set<SoundName>()
    for (const e of events) {
      if (e.seq <= lastSeq.current) continue
      const s = soundFor(e, seat)
      if (s) want.add(s)
    }
    lastSeq.current = maxSeq
    // One sound per kind per batch (an action that pays from several cards shouldn't
    // machine-gun the ding). A win supersedes everything else in the batch.
    if (want.has('win')) {
      playSound('win')
    } else {
      for (const s of ['dice', 'build', 'coinLoss', 'coinGain'] as const) {
        if (want.has(s)) playSound(s)
      }
    }
  }, [events, seat])

  useEffect(() => {
    if (activeSeat == null) return
    // Chime only when it BECOMES my turn (not on first mount).
    if (prevActive.current !== null && prevActive.current !== seat && activeSeat === seat) {
      playSound('turn')
    }
    prevActive.current = activeSeat
  }, [activeSeat, seat])

  return null
}

/** Which sound (if any) a keyed event should make for `seat`. */
function soundFor(e: KeyedEvent, seat: number): SoundName | null {
  switch (e.t) {
    case 'roll':
      return 'dice'
    case 'buy_card':
    case 'buy_landmark':
      return e.seat === seat ? 'build' : null
    case 'win':
    case 'win_forfeit':
      return 'win'
    case 'income':
    case 'tuna_payout':
    case 'loan_build':
    case 'city_hall':
      return e.seat === seat ? 'coinGain' : null
    case 'take':
      if (e.taker_seat === seat) return 'coinGain'
      if (e.payer_seat === seat) return 'coinLoss'
      return null
    case 'bank_pay':
      return e.seat === seat ? 'coinLoss' : null
    default:
      return null
  }
}
