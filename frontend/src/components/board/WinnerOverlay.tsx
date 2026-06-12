'use client'

import { useTranslations } from 'next-intl'

import type { GameState } from '@/types/game'
import { Button, Modal } from '@/components/ui'

interface WinnerOverlayProps {
  state: GameState
  mySeat: number | null
  onPlayAgain: () => void
  onBackToLobby: () => void
}

/**
 * Victory overlay. Shows when the server marks the game `finished`; the winner is
 * `state.winner`. Offers a rematch at the same table (`new_game`, which the backend
 * only honors with 2+ players connected) or a return to the lobby.
 */
export function WinnerOverlay({ state, mySeat, onPlayAgain, onBackToLobby }: WinnerOverlayProps) {
  const t = useTranslations('board')
  if (state.phase !== 'finished' || state.winner == null) return null

  const winner = state.players.find((p) => p.seat === state.winner)
  const iWon = mySeat != null && state.winner === mySeat

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
        <>
          <Button variant="ghost" onClick={onBackToLobby}>
            {t('backToLobby')}
          </Button>
          <Button onClick={onPlayAgain}>{t('playAgain')}</Button>
        </>
      }
    >
      <ul className="space-y-1">
        {state.players.map((p) => (
          <li key={p.seat} className="flex items-center justify-between font-body text-sm">
            <span>{p.name}</span>
            <span className="text-on-surface-variant">
              🏛 {p.landmarks.filter((lm) => lm.built).length} · 🪙 {p.coins}
            </span>
          </li>
        ))}
      </ul>
    </Modal>
  )
}
