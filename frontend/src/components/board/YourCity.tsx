'use client'

import { useTranslations } from 'next-intl'

import { cn } from '@/lib/cn'
import { familyStyleFromType } from '@/lib/families'
import { useCardName } from '@/lib/i18n-names'
import { diceLabel, symbolGlyph } from '@/lib/symbols'
import type { GameState, Landmark, Player } from '@/types/game'
import { CoinChip, DiceNumberBadge, PaperCard } from '@/components/ui'

import { GameLog } from './GameLog'

interface YourCityProps {
  state: GameState
  me: Player | undefined
  isMyTurn: boolean
  onBuildLandmark: (id: string) => void
}

/**
 * The "Your City" side drawer: the local player's owned establishments (grouped
 * with counts), the Milestones (landmark) grid, and a compact game log. Landmarks
 * are buildable on your build phase when affordable; clicking one sends a build.
 */
export function YourCity({ state, me, isMyTurn, onBuildLandmark }: YourCityProps) {
  const t = useTranslations('board')
  const cardName = useCardName()
  if (!me) return null

  const owned = Object.entries(me.cards)
    .filter(([, n]) => n > 0)
    .map(([id, n]) => ({ def: state.card_defs[id], n, id }))
    .filter((x) => x.def)
    .sort((a, b) => (a.def!.cost ?? 0) - (b.def!.cost ?? 0))

  const cardTotal = owned.reduce((sum, x) => sum + x.n, 0)

  return (
    <aside className="flex h-full w-full flex-col gap-4">
      {/* Owned establishments */}
      <PaperCard className="flex min-h-0 flex-1 flex-col p-4">
        <div className="mb-2 flex items-center justify-between">
          <h2 className="font-heading text-headline-md text-on-surface">{t('yourCity')}</h2>
          <span className="rounded-full bg-surface-container px-2 py-0.5 font-label text-xs text-on-surface-variant">
            {t('cardCount', { count: cardTotal })}
          </span>
        </div>
        <ul className="-mr-1 flex-1 space-y-1.5 overflow-y-auto pr-1">
          {owned.map(({ def, n, id }) => (
            <li
              key={id}
              className="flex items-center gap-2 rounded-lg bg-surface-container-low p-2"
            >
              <span
                className={cn('h-3 w-3 shrink-0 rounded-full', familyStyleFromType(def!.type).dot)}
                aria-hidden
              />
              <span className="text-lg" aria-hidden>
                {symbolGlyph(def!.symbol)}
              </span>
              <span className="min-w-0 flex-1 truncate font-label text-sm text-on-surface">
                {cardName(id, def!.name)}
              </span>
              <DiceNumberBadge value={diceLabel(def!.dice)} active={state.last_roll != null && def!.dice.includes(state.last_roll)} />
              <span className="font-number text-sm font-bold tabular text-on-surface-variant">
                {t('owned', { count: n })}
              </span>
            </li>
          ))}
        </ul>
      </PaperCard>

      {/* Milestones (landmarks) */}
      <PaperCard className="p-4">
        <h3 className="mb-2 font-label text-sm uppercase tracking-wide text-on-surface-variant">
          {t('milestones')}
        </h3>
        <div className="grid grid-cols-2 gap-2">
          {me.landmarks.map((lm) => (
            <Milestone
              key={lm.id}
              lm={lm}
              buyable={isMyTurn && state.phase === 'build' && !lm.built && me.coins >= lm.cost}
              onBuild={() => onBuildLandmark(lm.id)}
            />
          ))}
        </div>
      </PaperCard>

      {/* Log — localized from keyed events */}
      <PaperCard className="max-h-28 overflow-y-auto p-3">
        <GameLog state={state} />
      </PaperCard>
    </aside>
  )
}

function Milestone({
  lm,
  buyable,
  onBuild,
}: {
  lm: Landmark
  buyable: boolean
  onBuild: () => void
}) {
  const cardName = useCardName()
  return (
    <button
      type="button"
      disabled={!buyable}
      onClick={onBuild}
      aria-pressed={lm.built}
      className={cn(
        'flex flex-col items-start gap-1 rounded-lg border-2 p-2 text-left transition-colors',
        lm.built
          ? 'border-primary bg-primary-container/30'
          : buyable
            ? 'cursor-pointer border-dashed border-primary bg-surface-container-low hover:bg-primary-container/15'
            : 'border-dashed border-outline-variant bg-surface-container-low opacity-70',
      )}
    >
      <span className="flex w-full items-center justify-between">
        <span className="text-base" aria-hidden>
          🏛
        </span>
        {lm.built ? (
          <span className="font-label text-xs text-primary" aria-label="built">
            ✓
          </span>
        ) : (
          <CoinChip value={lm.cost} size="sm" />
        )}
      </span>
      <span className="line-clamp-2 font-label text-xs font-medium text-on-surface">
        {cardName(lm.id, lm.name)}
      </span>
    </button>
  )
}
