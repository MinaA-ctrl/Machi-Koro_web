'use client'

import { useTranslations } from 'next-intl'
import { useEffect, useRef, useState } from 'react'

import { familyFromType } from '@/lib/families'
import { useCardName } from '@/lib/i18n-names'
import type { CardDef, GameState, Player } from '@/types/game'
import { Button, CoinChip, Modal } from '@/components/ui'
import { EstablishmentCard } from './EstablishmentCard'

// Stable family ordering for the classic market: blue → green → red → purple.
const FAMILY_ORDER: Record<string, number> = { blue: 0, green: 1, red: 2, purple: 3, gold: 4 }

/** Lowest activation number on a card (its first die face) — for ascending sort. */
function minDice(card: CardDef): number {
  return card.dice.length > 0 ? Math.min(...card.dice) : 99
}

interface MarketProps {
  state: GameState
  me: Player | undefined
  isMyTurn: boolean
  onBuy: (id: string) => void
}

/**
 * The card market — establishment cards that wrap onto multiple rows to fit the
 * market column (rather than scrolling off in a single row). Each card knows
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
  const cardName = useCardName()
  const canBuyPhase = isMyTurn && state.phase === 'build'
  const lastRoll = state.last_roll
  const isVariableSupply = Array.isArray(state.deck)

  // Buying asks for confirmation first ("Buy X for N coins?") rather than firing
  // the build the instant a card is clicked.
  const [confirmCard, setConfirmCard] = useState<CardDef | null>(null)

  const confirmBuy = () => {
    if (confirmCard) onBuy(confirmCard.id)
    setConfirmCard(null)
  }

  // Organize the classic market by family color, then ascending activation number
  // (1 → up), then cost — so it reads left-to-right, top-to-bottom in a tidy order
  // and wraps cleanly across rows. Variable Supply keeps its fixed slot order so the
  // sold-out → reveal animation stays anchored to the right slot.
  const displayCards = isVariableSupply
    ? state.market
    : [...state.market].sort((a, b) => {
        const fam = (FAMILY_ORDER[familyFromType(a.type)] ?? 9) - (FAMILY_ORDER[familyFromType(b.type)] ?? 9)
        if (fam !== 0) return fam
        const dice = minDice(a) - minDice(b)
        if (dice !== 0) return dice
        return (a.cost ?? 0) - (b.cost ?? 0)
      })

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
    <section aria-label={t('market')} className="flex flex-col px-container-padding lg:min-h-0 lg:flex-1">
      <h2 className="mb-2 font-label text-sm uppercase tracking-wide text-inverse-on-surface/80">
        {t('market')}
      </h2>
      {/* Phone: a single horizontal carousel (swipe sideways) so the market doesn't
          become a tall multi-row block. Desktop (lg+): cards wrap into rows and only
          this box scrolls vertically, never the whole page. */}
      <div className="flex flex-nowrap content-start gap-card-gap overflow-x-auto pb-2 lg:flex-wrap lg:min-h-0 lg:flex-1 lg:overflow-x-visible lg:overflow-y-auto">
        {displayCards.map((card) => {
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
              onBuy={() => setConfirmCard(card)}
            />
          )
        })}
      </div>

      <Modal
        open={confirmCard != null}
        onClose={() => setConfirmCard(null)}
        title={t('buyConfirmTitle')}
        actions={
          <>
            <Button variant="ghost" onClick={() => setConfirmCard(null)}>
              {t('buyConfirmCancel')}
            </Button>
            <Button variant="primary" onClick={confirmBuy}>
              {t('buy')}
            </Button>
          </>
        }
      >
        {confirmCard && (
          <span className="flex flex-wrap items-center gap-1.5">
            {t('buyConfirmBody', { card: cardName(confirmCard.id, confirmCard.name) })}
            <CoinChip value={confirmCard.cost} size="sm" />
          </span>
        )}
      </Modal>
    </section>
  )
}
