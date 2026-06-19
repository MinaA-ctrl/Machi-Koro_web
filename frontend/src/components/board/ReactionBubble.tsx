'use client'

import { useEffect, useState } from 'react'

/**
 * A transient "thought bubble" emoji reaction shown above a player's avatar.
 * Driven by `{ emoji, ts }` from the game store: each new `ts` re-triggers the
 * pop-in animation and the bubble auto-dismisses after a few seconds.
 */
export function ReactionBubble({ reaction }: { reaction?: { emoji: string; ts: number } }) {
  const [shown, setShown] = useState<{ emoji: string; ts: number } | null>(null)

  useEffect(() => {
    if (!reaction) return
    setShown(reaction)
    const id = window.setTimeout(() => setShown(null), 3500)
    return () => window.clearTimeout(id)
  }, [reaction?.ts]) // eslint-disable-line react-hooks/exhaustive-deps

  if (!shown) return null

  return (
    <span
      key={shown.ts}
      className="pointer-events-none absolute -top-10 left-1/2 z-10 -translate-x-1/2 animate-reaction-pop select-none"
      aria-hidden
    >
      <span className="relative grid h-9 w-9 place-items-center rounded-full bg-surface-container-lowest text-xl shadow-card">
        {shown.emoji}
        {/* little bubble tail */}
        <span className="absolute -bottom-1 left-1/2 h-2 w-2 -translate-x-1/2 rotate-45 rounded-sm bg-surface-container-lowest shadow-card" />
      </span>
    </span>
  )
}
