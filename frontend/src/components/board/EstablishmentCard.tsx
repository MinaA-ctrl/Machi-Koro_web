'use client'

import { cn } from '@/lib/cn'
import { useCardName } from '@/lib/i18n-names'
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

  return (
    <PaperCard
      className={cn(
        'flex w-36 shrink-0 flex-col overflow-hidden transition-transform [transform-style:preserve-3d]',
        interactive && 'cursor-pointer hover:-translate-y-1 hover:shadow-card-hover active:translate-y-0 active:shadow-card-press',
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
        <span className="truncate">{cardName(card.id, card.name)}</span>
        <DiceNumberBadge value={diceLabel(card.dice)} active={activeOnRoll} />
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
          {card.effect}
        </p>
        <div className="mt-auto flex justify-end pt-1">
          <CoinChip value={card.cost} size="sm" />
        </div>
      </div>
    </PaperCard>
  )
}
