'use client'

import { useTranslations } from 'next-intl'

import { cn } from '@/lib/cn'
import type { GameState, Player } from '@/types/game'
import { CoinChip } from '@/components/ui'
import { LocaleSwitcher } from '@/components/LocaleSwitcher'

interface BoardTopBarProps {
  state: GameState
  me: Player | undefined
  isMyTurn: boolean
  activeName: string
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
export function BoardTopBar({ state, me, isMyTurn, activeName }: BoardTopBarProps) {
  const t = useTranslations('board')
  const phaseKey = PHASE_KEY[state.phase] ?? 'phasePending'

  const pillTone =
    state.phase === 'build'
      ? 'bg-primary-container text-on-primary-container'
      : state.phase === 'roll'
        ? 'bg-secondary-container text-on-secondary-container'
        : 'bg-tertiary-container text-on-tertiary-container'

  return (
    <header className="flex flex-wrap items-center gap-3 px-container-padding py-3">
      <span className="font-display text-headline-md font-semibold text-primary-container">
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
        <LocaleSwitcher />
        {me && (
          <span className="flex items-center gap-1.5 rounded-full bg-surface-container px-2 py-1 shadow-card">
            <CoinChip value={me.coins} size="md" />
          </span>
        )}
      </div>
    </header>
  )
}
