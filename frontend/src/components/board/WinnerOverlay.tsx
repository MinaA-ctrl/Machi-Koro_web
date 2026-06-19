'use client'

import { useTranslations } from 'next-intl'

import { computeStandings } from '@/lib/scoring'
import type { GameState } from '@/types/game'
import { Button, Modal } from '@/components/ui'

interface WinnerOverlayProps {
  state: GameState
  mySeat: number | null
  onBackToLobby: () => void
}

/**
 * Victory overlay. Shows when the server marks the game `finished`; the winner is
 * `state.winner`. Offers a rematch at the same table (`new_game`, which the backend
 * only honors with 2+ players connected) or a return to the lobby.
 */
export function WinnerOverlay({ state, mySeat, onBackToLobby }: WinnerOverlayProps) {
  const t = useTranslations('board')
  if (state.phase !== 'finished' || state.winner == null) return null

  const winner = state.players.find((p) => p.seat === state.winner)
  const iWon = mySeat != null && state.winner === mySeat
  const standings = computeStandings(state)

  return (
    <Modal
      open
      dismissable={false}
      title={
        <span className="flex items-center gap-2">
          <span aria-hidden>🏆</span>
          {iWon ? t('winnerYou') : t('winnerTitle', { name: winner?.name ?? '' })}
        </span>
      }
      actions={
        <Button variant="primary" onClick={onBackToLobby}>
          {t('backToLobby')}
        </Button>
      }
    >
      <ul className="space-y-1.5">
        {standings.map((s) => (
          <li
            key={s.seat}
            className="flex items-center justify-between gap-3 rounded-lg bg-surface-container-low px-3 py-2 font-body text-sm"
          >
            <span className="flex min-w-0 items-center gap-2">
              <span className="font-number font-bold text-on-surface-variant">{s.place}.</span>
              <span className="truncate text-on-surface">
                {s.name}
                {s.isWinner && <span aria-hidden> 🏆</span>}
              </span>
            </span>
            <span className="flex shrink-0 items-center gap-3 text-on-surface-variant">
              <span>🏛 {s.built}</span>
              <span className="font-number font-bold text-primary">{t('points', { points: s.points })}</span>
            </span>
          </li>
        ))}
      </ul>
    </Modal>
  )
}
