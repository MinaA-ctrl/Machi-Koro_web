'use client'

import { useTranslations } from 'next-intl'

import { useEventText } from '@/lib/use-event-text'
import type { GameState, KeyedEvent } from '@/types/game'
import { Modal } from '@/components/ui'

/**
 * Full game history dialog — opened from the "History" toggle in Your City. Groups
 * the keyed event stream into turns (each `roll` starts a new turn) and renders them
 * as bullet points: the turn header (who rolled + dice total) with the coin
 * payouts and the build/skip nested underneath. Centered, scrollable, closed via
 * the ✕ in the top-right (or backdrop / Escape). Falls back to the flat legacy log
 * if a snapshot predates keyed events.
 */
export function GameHistoryModal({
  open,
  onClose,
  state,
}: {
  open: boolean
  onClose: () => void
  state: GameState
}) {
  const t = useTranslations('board')
  const render = useEventText()
  const events = state.events ?? []
  const turns = groupByTurn(events)

  return (
    <Modal open={open} onClose={onClose} title={t('historyTitle')} showClose className="max-w-lg">
      <div className="max-h-[60vh] overflow-y-auto pr-1">
        {events.length === 0 ? (
          // Legacy snapshot without keyed events — flat list.
          <ul className="space-y-1 font-body text-sm text-on-surface-variant">
            {state.log.map((line, i) => (
              <li key={i}>{line}</li>
            ))}
          </ul>
        ) : (
          <ol className="space-y-3">
            {turns.map((turn, i) => (
              <li key={turn.header?.seq ?? `intro-${i}`}>
                {turn.header && (
                  <p className="flex items-center gap-1.5 font-label text-sm font-semibold text-on-surface">
                    <span aria-hidden>🎲</span>
                    {render(turn.header)}
                  </p>
                )}
                {turn.items.length > 0 && (
                  <ul className="mt-1 space-y-0.5 border-l-2 border-outline-variant pl-3 font-body text-sm text-on-surface-variant">
                    {turn.items.map((e) => (
                      <li key={e.seq} className="flex gap-1.5">
                        <span aria-hidden className="text-on-surface-variant/50">
                          •
                        </span>
                        <span>{render(e)}</span>
                      </li>
                    ))}
                  </ul>
                )}
              </li>
            ))}
          </ol>
        )}
      </div>
    </Modal>
  )
}

interface Turn {
  header: KeyedEvent | null
  items: KeyedEvent[]
}

/**
 * Split the ordered event stream into turns. Each `roll` (a new turn's dice) starts
 * a fresh group as its header; everything after — payouts, then the build/skip —
 * nests under it. Events before the first roll (game setup) form a headerless intro.
 */
function groupByTurn(events: KeyedEvent[]): Turn[] {
  const turns: Turn[] = []
  let current: Turn | null = null

  for (const e of events) {
    if (e.t === 'roll') {
      current = { header: e, items: [] }
      turns.push(current)
    } else if (current) {
      current.items.push(e)
    } else {
      // Leading events with no roll yet → a headerless intro bucket.
      if (turns.length === 0 || turns[0]!.header !== null) {
        turns.unshift({ header: null, items: [] })
      }
      turns[0]!.items.push(e)
    }
  }

  return turns
}
