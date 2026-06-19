'use client'

import { useTranslations } from 'next-intl'

import { useCardEffect, useCardName } from '@/lib/i18n-names'
import type { Landmark } from '@/types/game'
import { CoinChip, Modal } from '@/components/ui'

/**
 * Reference dialog for the landmarks — opened from the list button in the Landmarks
 * header. Lists every landmark with its localized name and what it does (and when),
 * so players can look up effects without enlarging the small landmark tiles. A ✓
 * marks the ones already built. Closed via the ✕ (or backdrop / Escape).
 */
export function LandmarkInfoModal({
  open,
  onClose,
  landmarks,
}: {
  open: boolean
  onClose: () => void
  landmarks: Landmark[]
}) {
  const t = useTranslations('board')
  const cardName = useCardName()
  const cardEffect = useCardEffect()

  return (
    <Modal open={open} onClose={onClose} showClose title={t('landmarkInfoTitle')} className="max-w-md">
      <ul className="max-h-[60vh] space-y-2 overflow-y-auto pr-1">
        {landmarks.map((lm) => (
          <li key={lm.id} className="rounded-lg bg-surface-container-low p-3">
            <div className="flex items-center justify-between gap-2">
              <span className="font-label text-sm font-semibold text-on-surface">
                <span aria-hidden>🏛 </span>
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
            <p className="mt-1 font-body text-sm leading-snug text-on-surface-variant">
              {cardEffect(lm.id, lm.effect)}
            </p>
          </li>
        ))}
      </ul>
    </Modal>
  )
}
