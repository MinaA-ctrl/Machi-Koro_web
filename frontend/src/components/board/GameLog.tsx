'use client'

import { useEventText } from '@/lib/use-event-text'
import type { GameState } from '@/types/game'

/**
 * The game log, localized from the engine's keyed `state.events` (the translatable
 * source of truth). Falls back to the English `state.log` only if a snapshot
 * predates keyed events. Shows the most recent `max` lines.
 */
export function GameLog({ state, max = 6 }: { state: GameState; max?: number }) {
  const render = useEventText()
  const events = state.events ?? []

  const lines =
    events.length > 0
      ? events.slice(-max).map((e) => ({ key: e.seq, text: render(e) }))
      : state.log.slice(-max).map((line, i) => ({ key: `legacy-${i}`, text: line }))

  return (
    <ul className="space-y-0.5 font-body text-xs text-on-surface-variant">
      {lines.map(({ key, text }) => (
        <li key={key}>{text}</li>
      ))}
    </ul>
  )
}
