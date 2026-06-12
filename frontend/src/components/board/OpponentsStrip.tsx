'use client'

import { useTranslations } from 'next-intl'

import { cn } from '@/lib/cn'
import { familyStyleFromType } from '@/lib/families'
import type { CardDef, Player } from '@/types/game'
import { CoinChip } from '@/components/ui'

interface OpponentsStripProps {
  opponents: Player[]
  activeSeat: number
  cardDefs: Record<string, CardDef>
}

/**
 * Horizontal strip of opponents: avatar · name · coins · a mini swatch of owned
 * card families · turn highlight ring. Mini-cards are family-colored dots with a
 * count, enough to read an opponent's board at a glance without the full city.
 */
export function OpponentsStrip({ opponents, activeSeat, cardDefs }: OpponentsStripProps) {
  const t = useTranslations('board')
  if (opponents.length === 0) return null

  return (
    <ul className="flex flex-wrap justify-center gap-3 px-container-padding py-2">
      {opponents.map((opp) => {
        const isActive = opp.seat === activeSeat
        const owned = Object.entries(opp.cards).filter(([, n]) => n > 0)
        const landmarksBuilt = opp.landmarks.filter((lm) => lm.built).length
        return (
          <li
            key={opp.seat}
            className={cn(
              'flex items-center gap-2 rounded-xl bg-surface-container-low px-3 py-2 shadow-card',
              isActive && 'ring-2 ring-primary ring-offset-2 ring-offset-secondary',
            )}
          >
            <span
              className="grid h-9 w-9 place-items-center rounded-full bg-surface-container text-lg shadow-felt"
              aria-hidden
            >
              🧑
            </span>
            <div className="min-w-0">
              <p className="flex items-center gap-1 font-label text-sm text-on-surface">
                <span className="max-w-24 truncate">{opp.name}</span>
                <CoinChip value={opp.coins} size="sm" />
              </p>
              <div className="mt-1 flex items-center gap-1" aria-label={t('cardCount', { count: owned.length })}>
                {owned.slice(0, 8).map(([id, n]) => {
                  const def = cardDefs[id]
                  return (
                    <span
                      key={id}
                      title={def ? `${def.name} ×${n}` : id}
                      className={cn('h-2.5 w-2.5 rounded-full', familyStyleFromType(def?.type).dot)}
                    />
                  )
                })}
                <span className="ml-1 font-label text-[10px] text-on-surface-variant">
                  🏛 {landmarksBuilt}
                </span>
              </div>
            </div>
          </li>
        )
      })}
    </ul>
  )
}
