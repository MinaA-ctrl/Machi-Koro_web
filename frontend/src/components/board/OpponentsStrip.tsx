'use client'

import { useState } from 'react'
import { useTranslations } from 'next-intl'

import { cn } from '@/lib/cn'
import { familyStyleFromType } from '@/lib/families'
import { useGameStore } from '@/store/game-store'
import type { CardDef, Player } from '@/types/game'
import { CoinChip } from '@/components/ui'

import { PlayerCityModal } from './PlayerCityModal'
import { ReactionBubble } from './ReactionBubble'

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
  const reactions = useGameStore((s) => s.reactions)
  const [openSeat, setOpenSeat] = useState<number | null>(null)
  if (opponents.length === 0) return null

  const openPlayer = opponents.find((o) => o.seat === openSeat) ?? null

  return (
    <>
    <ul className="flex flex-wrap justify-center gap-3 px-container-padding py-2">
      {opponents.map((opp) => {
        const isActive = opp.seat === activeSeat
        const owned = Object.entries(opp.cards).filter(([, n]) => n > 0)
        const landmarksBuilt = opp.landmarks.filter((lm) => lm.built).length
        return (
          <li
            key={opp.seat}
            role="button"
            tabIndex={0}
            onClick={() => setOpenSeat(opp.seat)}
            onKeyDown={(e) => {
              if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault()
                setOpenSeat(opp.seat)
              }
            }}
            aria-label={t('viewPlayerCity', { name: opp.name })}
            className={cn(
              'flex cursor-pointer items-center gap-2 rounded-xl bg-surface-container-low px-3 py-2 shadow-card transition-shadow hover:shadow-card-hover focus:outline-none focus-visible:ring-2 focus-visible:ring-primary',
              isActive && 'ring-2 ring-primary ring-offset-2 ring-offset-secondary',
            )}
          >
            <span className="relative">
              <ReactionBubble reaction={reactions[opp.seat]} />
              <span
                className="grid h-9 w-9 place-items-center rounded-full bg-surface-container text-lg shadow-felt"
                aria-hidden
              >
                🧑
              </span>
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
    <PlayerCityModal player={openPlayer} cardDefs={cardDefs} onClose={() => setOpenSeat(null)} />
    </>
  )
}
