'use client'

import { useEffect, useState } from 'react'
import { useTranslations } from 'next-intl'

import { cn } from '@/lib/cn'
import { isMuted, setMuted, unlockAudio } from '@/lib/sound'
import type { GameState } from '@/types/game'
import { Button, Modal } from '@/components/ui'
import { LocaleSwitcher } from '@/components/LocaleSwitcher'

interface BoardTopBarProps {
  state: GameState
  isMyTurn: boolean
  activeName: string
  /** Leave the game and return to the lobby. */
  onLeave: () => void
}

const PHASE_KEY: Record<string, 'phaseRoll' | 'phaseBuild' | 'phasePending'> = {
  roll: 'phaseRoll',
  build: 'phaseBuild',
}

/**
 * Board top bar: wordmark · turn banner · phase pill · my coin balance. The phase
 * pill color tracks the phase (gold for build, felt for roll, clay for a pending
 * choice) so a glance tells you what the game is waiting on.
 */
export function BoardTopBar({ state, isMyTurn, activeName, onLeave }: BoardTopBarProps) {
  const t = useTranslations('board')
  const [confirmLeave, setConfirmLeave] = useState(false)
  // Read the persisted mute preference after mount (localStorage is client-only, so
  // starting `false` keeps the server/first-client render in agreement).
  const [muted, setMutedState] = useState(false)
  useEffect(() => setMutedState(isMuted()), [])
  const phaseKey = PHASE_KEY[state.phase] ?? 'phasePending'

  const toggleSound = () => {
    const next = !muted
    setMuted(next)
    setMutedState(next)
    if (!next) unlockAudio()
  }

  const pillTone =
    state.phase === 'build'
      ? 'bg-primary-container text-on-primary-container'
      : state.phase === 'roll'
        ? 'bg-secondary-container text-on-secondary-container'
        : 'bg-tertiary-container text-on-tertiary-container'

  return (
    <header className="flex flex-wrap items-center gap-3 px-container-padding py-3">
      <span className="hidden font-display text-headline-md font-semibold text-primary-container sm:inline">
        Machi&nbsp;Koro
      </span>

      <div
        className={cn(
          'rounded-full px-4 py-1.5 font-label text-sm font-medium shadow-card',
          isMyTurn ? 'bg-primary text-on-primary' : 'bg-surface-container text-on-surface-variant',
        )}
        aria-live="polite"
      >
        {isMyTurn ? t('yourTurn') : t('playerTurn', { name: activeName })}
      </div>

      <span className={cn('rounded-full px-3 py-1 font-label text-xs uppercase tracking-wide', pillTone)}>
        {t(phaseKey)}
      </span>

      <div className="ml-auto flex items-center gap-3">
        <button
          type="button"
          onClick={toggleSound}
          aria-label={muted ? t('soundOn') : t('soundOff')}
          aria-pressed={!muted}
          className="grid h-9 w-9 place-items-center rounded-full bg-surface-container text-lg shadow-card transition-transform hover:scale-105"
        >
          <span aria-hidden>{muted ? '🔇' : '🔊'}</span>
        </button>
        <LocaleSwitcher />
        <Button variant="ghost" size="sm" onClick={() => setConfirmLeave(true)}>
          {t('leave')}
        </Button>
      </div>

      <Modal
        open={confirmLeave}
        onClose={() => setConfirmLeave(false)}
        title={t('leaveConfirmTitle')}
        actions={
          <>
            <Button variant="ghost" onClick={() => setConfirmLeave(false)}>
              {t('leaveCancel')}
            </Button>
            <Button variant="primary" onClick={onLeave}>
              {t('leaveConfirm')}
            </Button>
          </>
        }
      >
        <p>{t('leaveConfirmBody')}</p>
      </Modal>
    </header>
  )
}
