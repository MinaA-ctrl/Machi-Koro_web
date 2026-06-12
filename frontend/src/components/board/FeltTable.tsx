'use client'

import { useTranslations } from 'next-intl'

import type { GameState, Player } from '@/types/game'
import { Button } from '@/components/ui'
import { Dice } from './Dice'

interface FeltTableProps {
  state: GameState
  me: Player | undefined
  isMyTurn: boolean
  onRoll: (diceCount: 1 | 2) => void
  onEndTurn: () => void
  onTechInvest: () => void
}

/**
 * The green felt play area — dice + the turn's primary action. In the roll phase
 * the active player rolls (one button, or a 1-die/2-die choice once they own Train
 * Station); in the build phase they buy from the market or end their turn. Everyone
 * else sees whose move it is.
 */
export function FeltTable({ state, me, isMyTurn, onRoll, onEndTurn, onTechInvest }: FeltTableProps) {
  const t = useTranslations('board')
  const ownsTrainStation = !!me?.landmarks.some((lm) => lm.id === 'train_station' && lm.built)
  // Sharp Tech Startup: invest once per turn during your build phase while you own
  // the card and can pay the 1-coin stake.
  const canInvest =
    isMyTurn &&
    state.phase === 'build' &&
    !state.tech_invest_used &&
    (me?.cards['tech_startup'] ?? 0) > 0 &&
    (me?.coins ?? 0) >= 1

  return (
    <div className="felt-panel mx-container-padding rounded-xl px-6 py-8">
      <div className="flex flex-col items-center gap-6">
        <Dice dice={state.last_dice} />

        {state.phase === 'roll' && isMyTurn && (
          <div className="flex gap-3">
            {ownsTrainStation ? (
              <>
                <Button variant="primary" size="lg" onClick={() => onRoll(1)}>
                  {t('rollOneDie')}
                </Button>
                <Button variant="primary" size="lg" onClick={() => onRoll(2)}>
                  {t('rollTwoDice')}
                </Button>
              </>
            ) : (
              <Button variant="primary" size="lg" leading={<span aria-hidden>🎲</span>} onClick={() => onRoll(1)}>
                {t('rollDice')}
              </Button>
            )}
          </div>
        )}

        {state.phase === 'build' && isMyTurn && (
          <div className="flex flex-wrap items-center justify-center gap-3">
            {canInvest && (
              <Button variant="ghost" size="lg" className="bg-surface-container-lowest" onClick={onTechInvest} leading={<span aria-hidden>🚀</span>}>
                {t('techInvest')}
              </Button>
            )}
            <Button variant="secondary" size="lg" onClick={onEndTurn}>
              {t('endTurn')}
            </Button>
          </div>
        )}

        {!isMyTurn && state.phase !== 'finished' && (
          <p className="font-body text-body-md text-inverse-on-surface/85" aria-live="polite">
            {t('playerTurn', { name: playerName(state, state.active_seat) })}
          </p>
        )}
      </div>
    </div>
  )
}

function playerName(state: GameState, seat: number): string {
  return state.players.find((p) => p.seat === seat)?.name ?? `#${seat}`
}
