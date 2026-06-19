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
  /** Send an emoji reaction to the table. */
  onReact: (emoji: string) => void
}

/** The quick-reaction palette shown on the right of the felt. */
const REACTIONS = ['👍', '😂', '😮', '🎉', '😢', '🔥'] as const

/**
 * The green felt play area — dice + the turn's primary action. In the roll phase
 * the active player rolls (one button, or a 1-die/2-die choice once they own Train
 * Station); in the build phase they buy from the market or end their turn. Everyone
 * else sees whose move it is.
 */
export function FeltTable({ state, me, isMyTurn, onRoll, onEndTurn, onTechInvest, onReact }: FeltTableProps) {
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
    <div className="felt-panel relative mx-container-padding rounded-xl px-6 py-4">
      {/* Play column — nudged left of centre so the reaction bar has room on the right. */}
      <div className="flex flex-col items-center gap-4 sm:pr-24">
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

      {/* Reaction bar. On phones it flows as a centered wrapped row UNDER the dice/
          actions (no overlap); from `sm` up it's a 2-column grid pinned to the right
          of the felt (the play column reserves space via `sm:pr-24`). */}
      <div
        className="mt-4 flex flex-wrap justify-center gap-2 sm:absolute sm:right-3 sm:top-1/2 sm:mt-0 sm:grid sm:-translate-y-1/2 sm:grid-cols-2"
        role="group"
        aria-label={t('reactions')}
      >
        {REACTIONS.map((emoji) => (
          <button
            key={emoji}
            type="button"
            onClick={() => onReact(emoji)}
            aria-label={t('reactWith', { emoji })}
            className="grid h-9 w-9 place-items-center rounded-full bg-surface-container-lowest/85 text-lg shadow-card transition-transform hover:scale-110 active:scale-95"
          >
            {emoji}
          </button>
        ))}
      </div>
    </div>
  )
}

function playerName(state: GameState, seat: number): string {
  return state.players.find((p) => p.seat === seat)?.name ?? `#${seat}`
}
