'use client'

import { cn } from '@/lib/cn'
import { useCardEffect, useCardName } from '@/lib/i18n-names'
import { diceLabel, symbolGlyph } from '@/lib/symbols'
import type { CardDef } from '@/types/game'
import { CoinChip, DiceNumberBadge, FamilyBand, PaperCard } from '@/components/ui'

interface EstablishmentCardProps {
  card: CardDef
  /** Copies left in supply (market). */
  remaining?: number
  /** Show the remaining count prominently as a chip (Variable Supply mode). */
  showRemaining?: boolean
  /** Play the flip-reveal entrance (a freshly-drawn Variable-Supply slot). */
  revealing?: boolean
  /** Will this card activate on the current roll? Highlights the badge. */
  activeOnRoll?: boolean
  /** Affordable + buyable right now (active player, build phase). */
  buyable?: boolean
  onBuy?: (id: string) => void
}

/**
 * A market establishment card: cream paper, family header band with the activation
 * number, symbol glyph, effect text, and a cost coin. When `buyable`, the whole
 * card is a button that lifts on hover and presses down on click (token feel).
 */
export function EstablishmentCard({
  card,
  remaining,
  showRemaining = false,
  revealing = false,
  activeOnRoll = false,
  buyable = false,
  onBuy,
}: EstablishmentCardProps) {
  const soldOut = remaining === 0
  const interactive = buyable && !soldOut
  const cardName = useCardName()
  const cardEffect = useCardEffect()

  return (
    <PaperCard
      className={cn(
        'group relative flex w-36 shrink-0 flex-col overflow-hidden transition-transform [transform-style:preserve-3d]',
        // Grow ~10% on hover/focus so the card is easier to read (and the full name
        // un-truncates, below); raise it above neighbours while enlarged.
        'hover:z-20 hover:scale-110 focus-within:z-20 focus-within:scale-110',
        interactive && 'cursor-pointer hover:shadow-card-hover active:scale-100 active:shadow-card-press',
        soldOut && 'opacity-45 saturate-50',
        revealing && 'animate-card-reveal',
      )}
      role={interactive ? 'button' : undefined}
      tabIndex={interactive ? 0 : undefined}
      aria-disabled={!interactive}
      onClick={interactive ? () => onBuy?.(card.id) : undefined}
      onKeyDown={
        interactive
          ? (e) => {
              if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault()
                onBuy?.(card.id)
              }
            }
          : undefined
      }
    >
      <FamilyBand type={card.type}>
        {/* Truncate by default so long names (Farmers Market, Food Warehouse,
            Family Restaurant) keep the name + activation badge on one row;
            `min-w-0` lets the flex item actually shrink. On hover/focus the card
            is enlarged and the name un-truncates so the whole name is visible. */}
        <span
          title={cardName(card.id, card.name)}
          className="min-w-0 truncate group-hover:overflow-visible group-hover:whitespace-normal group-focus-within:overflow-visible group-focus-within:whitespace-normal"
        >
          {cardName(card.id, card.name)}
        </span>
        <DiceNumberBadge value={diceLabel(card.dice)} active={activeOnRoll} className="shrink-0" />
      </FamilyBand>

      <div className="flex flex-1 flex-col gap-1 p-2">
        <div className="flex items-center justify-between">
          <span className="text-2xl" aria-hidden>
            {symbolGlyph(card.symbol)}
          </span>
          {typeof remaining === 'number' &&
            (showRemaining ? (
              <span
                className={cn(
                  'rounded-full px-1.5 py-0.5 font-label text-[10px] font-medium',
                  remaining <= 1
                    ? 'bg-error-container text-on-error-container'
                    : 'bg-surface-container text-on-surface-variant',
                )}
              >
                {remaining}
              </span>
            ) : (
              <span className="font-label text-xs text-on-surface-variant">×{remaining}</span>
            ))}
        </div>
        <p className="line-clamp-3 font-body text-[11px] leading-snug text-on-surface-variant">
          {cardEffect(card.id, card.effect)}
        </p>
        <div className="mt-auto flex justify-end pt-1">
          <CoinChip value={card.cost} size="sm" />
        </div>
      </div>
    </PaperCard>
  )
}
