'use client'

import { useTranslations } from 'next-intl'
import { useEffect, useState } from 'react'

import { cn } from '@/lib/cn'
import { familyStyleFromType } from '@/lib/families'
import { useCardName } from '@/lib/i18n-names'
import { symbolGlyph } from '@/lib/symbols'
import type { GamePrompt, GameState } from '@/types/game'
import { Button, CoinChip, Modal } from '@/components/ui'

export interface PromptHandlers {
  onYesNo: (answer: boolean) => void
  onTunaRoll: () => void
  onTvStationPick: (seat: number) => void
  onCleaningPick: (cardType: string) => void
  onDemolitionPick: (landmarkId: string) => void
  onMovingPick: (cardId: string, targetSeat: number) => void
  onBusinessTrade: (myCard: string, oppSeat: number, oppCard: string) => void
  onBusinessSkip: () => void
}

interface PromptOverlayProps {
  prompt: GamePrompt | null
  state: GameState
  handlers: PromptHandlers
}

/**
 * Interactive prompt overlay — renders the structured `game_prompt` payload from
 * the engine. One modal shell, a body per prompt type. The server validates every
 * response against the active seat + phase, and auto-applies a default on timeout,
 * so these UIs only need to gather a valid choice.
 */
export function PromptOverlay({ prompt, state, handlers }: PromptOverlayProps) {
  const t = useTranslations('board')
  const nameOf = useCardName()
  if (!prompt) return null

  const cardName = (id: string) => nameOf(id, state.card_defs[id]?.name)
  const landmarkName = (id: string) => {
    for (const p of state.players) {
      const lm = p.landmarks.find((l) => l.id === id)
      if (lm) return nameOf(id, lm.name)
    }
    return nameOf(id)
  }

  switch (prompt.type) {
    case 'harbor_bonus':
      return (
        <YesNoModal
          title={t('promptTitle')}
          body={t('promptHarbor', {
            roll: prompt.params.roll,
            total: prompt.params.total_with_bonus ?? prompt.params.roll + 2,
          })}
          onYes={() => handlers.onYesNo(true)}
          onNo={() => handlers.onYesNo(false)}
        />
      )
    case 'reroll':
      return (
        <YesNoModal
          title={t('promptTitle')}
          body={t('promptReroll', { roll: prompt.params.roll })}
          onYes={() => handlers.onYesNo(true)}
          onNo={() => handlers.onYesNo(false)}
        />
      )
    case 'tuna_roll':
      return (
        <Modal
          open
          dismissable={false}
          title={t('promptTitle')}
          actions={
            <Button onClick={handlers.onTunaRoll} leading={<span aria-hidden>🎲</span>}>
              {t('rollForTuna')}
            </Button>
          }
        >
          <p>{t('promptTuna')}</p>
        </Modal>
      )

    case 'tv_station':
      return (
        <Modal open dismissable={false} title={t('tvTitle')}>
          <p className="mb-3">{t('tvBody')}</p>
          <ul className="space-y-2">
            {prompt.params.opponents.map((opp) => (
              <li key={opp.seat}>
                <button
                  type="button"
                  onClick={() => handlers.onTvStationPick(opp.seat)}
                  className="flex w-full items-center justify-between rounded-lg border-2 border-outline-variant bg-surface-container-low px-3 py-2 text-left transition-colors hover:border-primary hover:bg-primary-container/15"
                >
                  <span className="font-label text-on-surface">{opp.name}</span>
                  <CoinChip value={opp.coins} size="sm" />
                </button>
              </li>
            ))}
          </ul>
        </Modal>
      )

    case 'cleaning_company':
      return (
        <Modal open dismissable={false} title={t('cleaningTitle')}>
          <p className="mb-3">{t('cleaningBody')}</p>
          <div className="grid grid-cols-2 gap-2">
            {prompt.params.targets.map((id) => {
              const def = state.card_defs[id]
              return (
                <button
                  key={id}
                  type="button"
                  onClick={() => handlers.onCleaningPick(id)}
                  className="flex items-center gap-2 rounded-lg border-2 border-outline-variant bg-surface-container-low px-3 py-2 text-left transition-colors hover:border-primary hover:bg-primary-container/15"
                >
                  <span
                    className={cn('h-3 w-3 shrink-0 rounded-full', familyStyleFromType(def?.type).dot)}
                    aria-hidden
                  />
                  <span className="text-lg" aria-hidden>
                    {symbolGlyph(def?.symbol)}
                  </span>
                  <span className="min-w-0 truncate font-label text-sm">{cardName(id)}</span>
                </button>
              )
            })}
          </div>
        </Modal>
      )

    case 'demolition':
      return (
        <Modal open dismissable={false} title={t('demolitionTitle')}>
          <p className="mb-3">{t('demolitionBody')}</p>
          <ul className="space-y-2">
            {prompt.params.targets.map((id) => (
              <li key={id}>
                <button
                  type="button"
                  onClick={() => handlers.onDemolitionPick(id)}
                  className="flex w-full items-center gap-2 rounded-lg border-2 border-outline-variant bg-surface-container-low px-3 py-2 text-left transition-colors hover:border-error hover:bg-error-container/30"
                >
                  <span aria-hidden>🏛</span>
                  <span className="font-label text-on-surface">{landmarkName(id)}</span>
                </button>
              </li>
            ))}
          </ul>
        </Modal>
      )

    case 'moving_company':
      return <MovingPrompt prompt={prompt} state={state} handlers={handlers} />

    case 'business_center':
      return <BusinessPrompt prompt={prompt} state={state} handlers={handlers} />

    default:
      return null
  }
}

// ── shared yes/no shell ─────────────────────────────────────────────────────────
function YesNoModal({
  title,
  body,
  onYes,
  onNo,
}: {
  title: string
  body: string
  onYes: () => void
  onNo: () => void
}) {
  const t = useTranslations('board')
  return (
    <Modal
      open
      dismissable={false}
      title={title}
      actions={
        <>
          <Button variant="ghost" onClick={onNo}>
            {t('no')}
          </Button>
          <Button onClick={onYes}>{t('yes')}</Button>
        </>
      }
    >
      <p>{body}</p>
    </Modal>
  )
}

// ── Moving Company: pick a card, then a recipient ───────────────────────────────
function MovingPrompt({
  prompt,
  state,
  handlers,
}: {
  prompt: Extract<GamePrompt, { type: 'moving_company' }>
  state: GameState
  handlers: PromptHandlers
}) {
  const t = useTranslations('board')
  const nameOf = useCardName()
  const [card, setCard] = useState<string | null>(null)
  const cardName = (id: string) => nameOf(id, state.card_defs[id]?.name)
  const seatName = (seat: number) => state.players.find((p) => p.seat === seat)?.name ?? `#${seat}`

  return (
    <Modal open dismissable={false} title={t('movingTitle')}>
      <p className="mb-3">{t('movingBody')}</p>

      <p className="mb-1 font-label text-sm text-on-surface-variant">{t('movingPickCard')}</p>
      <div className="mb-4 flex flex-wrap gap-2">
        {prompt.params.giveable.map((id) => {
          const def = state.card_defs[id]
          return (
            <button
              key={id}
              type="button"
              onClick={() => setCard(id)}
              className={cn(
                'flex items-center gap-1.5 rounded-full border-2 px-3 py-1.5 transition-colors',
                card === id
                  ? 'border-primary bg-primary-container/25'
                  : 'border-outline-variant bg-surface-container-low hover:border-outline',
              )}
            >
              <span className={cn('h-2.5 w-2.5 rounded-full', familyStyleFromType(def?.type).dot)} aria-hidden />
              <span className="font-label text-sm">{cardName(id)}</span>
            </button>
          )
        })}
      </div>

      {card && (
        <>
          <p className="mb-1 font-label text-sm text-on-surface-variant">{t('movingPickTarget')}</p>
          <div className="flex flex-wrap gap-2">
            {prompt.params.targets.map((seat) => (
              <Button key={seat} variant="secondary" size="sm" onClick={() => handlers.onMovingPick(card, seat)}>
                {seatName(seat)}
              </Button>
            ))}
          </div>
        </>
      )}
    </Modal>
  )
}

// ── Business Center: pick one of yours + one of theirs to swap ──────────────────
function BusinessPrompt({
  prompt,
  state,
  handlers,
}: {
  prompt: Extract<GamePrompt, { type: 'business_center' }>
  state: GameState
  handlers: PromptHandlers
}) {
  const t = useTranslations('board')
  const nameOf = useCardName()
  const [mine, setMine] = useState<string | null>(null)
  const [theirs, setTheirs] = useState<{ seat: number; card: string } | null>(null)
  const cardName = (id: string) => nameOf(id, state.card_defs[id]?.name)

  // Reset selections if the prompt instance changes.
  useEffect(() => {
    setMine(null)
    setTheirs(null)
  }, [prompt.promptId, prompt.active_seat])

  const chip = (key: string, cardId: string, selected: boolean, onClick: () => void) => {
    const def = state.card_defs[cardId]
    return (
      <button
        key={key}
        type="button"
        onClick={onClick}
        className={cn(
          'flex items-center gap-1.5 rounded-full border-2 px-2.5 py-1 transition-colors',
          selected
            ? 'border-primary bg-primary-container/25'
            : 'border-outline-variant bg-surface-container-low hover:border-outline',
        )}
      >
        <span className={cn('h-2.5 w-2.5 rounded-full', familyStyleFromType(def?.type).dot)} aria-hidden />
        <span className="font-label text-xs">{cardName(cardId)}</span>
      </button>
    )
  }

  return (
    <Modal
      open
      dismissable={false}
      title={t('businessTitle')}
      actions={
        <>
          <Button variant="ghost" onClick={handlers.onBusinessSkip}>
            {t('skip')}
          </Button>
          <Button
            disabled={!mine || !theirs}
            onClick={() => mine && theirs && handlers.onBusinessTrade(mine, theirs.seat, theirs.card)}
          >
            {t('businessTrade')}
          </Button>
        </>
      }
    >
      <p className="mb-3">{t('businessBody')}</p>

      <p className="mb-1 font-label text-sm text-on-surface-variant">{t('businessYouGive')}</p>
      <div className="mb-4 flex flex-wrap gap-1.5">
        {prompt.params.my_cards.map((id) => chip(id, id, mine === id, () => setMine(id)))}
      </div>

      <p className="mb-1 font-label text-sm text-on-surface-variant">{t('businessYouTake')}</p>
      <div className="space-y-2">
        {prompt.params.opponents.map((opp) => (
          <div key={opp.seat}>
            <p className="font-label text-xs text-on-surface">{opp.name}</p>
            <div className="mt-1 flex flex-wrap gap-1.5">
              {opp.cards.map((id) =>
                chip(`${opp.seat}:${id}`, id, theirs?.seat === opp.seat && theirs.card === id, () =>
                  setTheirs({ seat: opp.seat, card: id }),
                ),
              )}
            </div>
          </div>
        ))}
      </div>
    </Modal>
  )
}
