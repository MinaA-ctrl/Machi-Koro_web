'use client'

import { useEffect, useRef } from 'react'

import { useToast } from '@/components/ui'
import { useEventText } from '@/lib/use-event-text'
import { useGameStore } from '@/store/game-store'
import type { KeyedEvent } from '@/types/game'

/**
 * Watches the keyed-event stream and toasts whenever MY seat's coins change, with
 * the reason: gains in green ("…gets 3🪙 (Wheat Field)"), deductions in red
 * ("…pays 2🪙 …") so a loss is easy to distinguish at a glance. Renders nothing.
 * Tracks the last event `seq` it has seen so each change notifies exactly once; on
 * the first snapshot it primes that high-water mark without firing, so a reconnect
 * doesn't replay history.
 */
export function CoinGainNotifier({ seat }: { seat: number }) {
  const { show } = useToast()
  const render = useEventText()
  const events = useGameStore((s) => s.state?.events)
  const lastSeq = useRef<number | null>(null)

  useEffect(() => {
    if (!events || events.length === 0) return
    const maxSeq = events[events.length - 1]!.seq

    // First snapshot: prime the high-water mark, don't replay past changes.
    if (lastSeq.current === null) {
      lastSeq.current = maxSeq
      return
    }

    for (const e of events) {
      if (e.seq <= lastSeq.current) continue
      if (isMyGain(e, seat)) show(render(e), 'success')
      else if (isMyLoss(e, seat)) show(render(e), 'error')
    }
    lastSeq.current = maxSeq
  }, [events, seat, render, show])

  return null
}

/** True when keyed event `e` represents coins flowing TO `seat`. */
function isMyGain(e: KeyedEvent, seat: number): boolean {
  const amount = Number(e.amount ?? 0)
  switch (e.t) {
    case 'income':
    case 'tuna_payout':
      return e.seat === seat && amount > 0
    case 'take':
      return e.taker_seat === seat && amount > 0
    case 'loan_build': // fixed +5 from the Loan Office on build
    case 'city_hall': // floor top-up to 1🪙
      return e.seat === seat
    default:
      return false
  }
}

/** True when keyed event `e` represents coins flowing AWAY FROM `seat`. */
function isMyLoss(e: KeyedEvent, seat: number): boolean {
  const amount = Number(e.amount ?? 0)
  switch (e.t) {
    case 'take': // an opponent took coins from me
      return e.payer_seat === seat && amount > 0
    case 'bank_pay': // I paid the bank (e.g. Tax Office)
      return e.seat === seat && amount > 0
    default:
      return false
  }
}
