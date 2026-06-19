'use client'

import { useTranslations } from 'next-intl'

import { cn } from '@/lib/cn'
import { familyStyleFromType } from '@/lib/families'
import { useCardName } from '@/lib/i18n-names'
import { diceLabel, symbolGlyph } from '@/lib/symbols'
import type { CardDef, Player } from '@/types/game'
import { CoinChip, DiceNumberBadge, Modal } from '@/components/ui'

/**
 * Read-only "city" of any player, opened by tapping them in the opponents strip:
 * their owned establishments (grouped with counts, family-colored) and which
 * landmarks they've opened. Purely informational — no actions.
 */
export function PlayerCityModal({
  player,
  cardDefs,
  onClose,
}: {
  player: Player | null
  cardDefs: Record<string, CardDef>
  onClose: () => void
}) {
  const t = useTranslations('board')
  const cardName = useCardName()

  const owned = player
    ? Object.entries(player.cards)
        .filter(([, n]) => n > 0)
        .map(([id, n]) => ({ def: cardDefs[id], n, id }))
        .filter((x) => x.def)
        .sort((a, b) => (a.def!.cost ?? 0) - (b.def!.cost ?? 0))
    : []

  return (
    <Modal
      open={player != null}
      onClose={onClose}
      showClose
      className="max-w-md"
      title={
        player ? (
          <span className="flex items-center gap-2">
            <span aria-hidden>🧑</span>
            <span className="truncate">{player.name}</span>
            <CoinChip value={player.coins} size="sm" />
          </span>
        ) : undefined
      }
    >
      {player && (
        <div className="space-y-4">
          {/* Owned establishments */}
          <div>
            <h3 className="mb-2 font-label text-sm uppercase tracking-wide text-on-surface-variant">
              {t('cardCount', { count: owned.reduce((s, x) => s + x.n, 0) })}
            </h3>
            {owned.length === 0 ? (
              <p className="font-body text-sm text-on-surface-variant">—</p>
            ) : (
              <ul className="max-h-64 space-y-1.5 overflow-y-auto pr-1">
                {owned.map(({ def, n, id }) => (
                  <li key={id} className="flex items-center gap-2 rounded-lg bg-surface-container-low p-2">
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
                    <DiceNumberBadge value={diceLabel(def!.dice)} />
                    <span className="font-number text-sm font-bold tabular text-on-surface-variant">
                      {t('owned', { count: n })}
                    </span>
                  </li>
                ))}
              </ul>
            )}
          </div>

          {/* Milestones (landmarks) */}
          <div>
            <h3 className="mb-2 font-label text-sm uppercase tracking-wide text-on-surface-variant">
              {t('milestones')}
            </h3>
            <div className="grid grid-cols-2 gap-2">
              {player.landmarks.map((lm) => (
                <div
                  key={lm.id}
                  className={cn(
                    'flex items-center justify-between gap-1 rounded-lg border-2 p-2',
                    lm.built
                      ? 'border-primary bg-primary-container/30'
                      : 'border-dashed border-outline-variant bg-surface-container-low opacity-70',
                  )}
                >
                  <span className="line-clamp-2 font-label text-xs font-medium text-on-surface">
                    {cardName(lm.id, lm.name)}
                  </span>
                  {lm.built ? (
                    <span className="font-label text-xs text-primary" aria-label="built">
                      ✓
                    </span>
                  ) : (
                    <CoinChip value={lm.cost} size="sm" />
                  )}
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </Modal>
  )
}
