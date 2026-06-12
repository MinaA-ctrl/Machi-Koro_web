'use client'

import { useTranslations } from 'next-intl'
import { useEffect, useRef, useState } from 'react'

import type { GameState, Player } from '@/types/game'
import { EstablishmentCard } from './EstablishmentCard'

interface MarketProps {
  state: GameState
  me: Player | undefined
  isMyTurn: boolean
  onBuy: (id: string) => void
}

/**
 * The card market — a horizontal row of establishment cards. Each card knows
 * whether it would activate on the current roll (badge highlight), how many copies
 * remain (`state.supply`), and whether the local player can buy it right now
 * (their turn · build phase · can afford · in stock). Server re-validates every buy.
 *
 * 10-card Variable Supply: when `state.deck` is present a sold-out stack is replaced
 * by a freshly-drawn type. We detect the swap by diffing the visible card ids across
 * snapshots and play the flip-reveal on the new slot(s) (reduced-motion → fade).
 */
export function Market({ state, me, isMyTurn, onBuy }: MarketProps) {
  const t = useTranslations('board')
  const canBuyPhase = isMyTurn && state.phase === 'build'
  const lastRoll = state.last_roll
  const isVariableSupply = Array.isArray(state.deck)

  // Track which card ids just appeared so we can animate only those.
  const prevIds = useRef<Set<string>>(new Set(state.market.map((c) => c.id)))
  const [revealed, setRevealed] = useState<Set<string>>(new Set())

  useEffect(() => {
    const current = state.market.map((c) => c.id)
    const fresh = current.filter((id) => !prevIds.current.has(id))
    prevIds.current = new Set(current)
    if (fresh.length > 0) {
      setRevealed(new Set(fresh))
      const id = window.setTimeout(() => setRevealed(new Set()), 500)
      return () => window.clearTimeout(id)
    }
  }, [state.market])

  return (
    <section aria-label={t('market')} className="px-container-padding">
      <h2 className="mb-2 font-label text-sm uppercase tracking-wide text-inverse-on-surface/80">
        {t('market')}
      </h2>
      <div className="flex gap-card-gap overflow-x-auto pb-2">
        {state.market.map((card) => {
          const remaining = state.supply[card.id] ?? 0
          const affordable = (me?.coins ?? 0) >= card.cost
          const activeOnRoll = lastRoll != null && card.dice.includes(lastRoll)
          return (
            <EstablishmentCard
              key={card.id}
              card={card}
              remaining={remaining}
              showRemaining={isVariableSupply}
              revealing={revealed.has(card.id)}
              activeOnRoll={activeOnRoll}
              buyable={canBuyPhase && affordable && remaining > 0}
              onBuy={onBuy}
            />
          )
        })}
      </div>
    </section>
  )
}
