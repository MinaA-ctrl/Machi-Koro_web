'use client'

import { useEffect, useRef, useState } from 'react'

import { cn } from '@/lib/cn'
import { usePrefersReducedMotion } from '@/lib/use-prefers-reduced-motion'

// Pip layout per face (3×3 grid cells that are filled for each value).
const PIPS: Record<number, number[]> = {
  1: [4],
  2: [0, 8],
  3: [0, 4, 8],
  4: [0, 2, 6, 8],
  5: [0, 2, 4, 6, 8],
  6: [0, 2, 3, 5, 6, 8],
}

function DieFace({ value, tumbling }: { value: number; tumbling: boolean }) {
  const filled = PIPS[value] ?? PIPS[1]!
  return (
    <div
      className={cn(
        'grid h-16 w-16 grid-cols-3 grid-rows-3 gap-1 rounded-lg bg-surface-container-lowest p-2 shadow-float paper-edge',
        tumbling && 'animate-dice-tumble',
      )}
      role="img"
      aria-label={`Die showing ${value}`}
    >
      {Array.from({ length: 9 }).map((_, i) => (
        <span
          key={i}
          className={cn('place-self-center rounded-full', filled.includes(i) ? 'h-3 w-3 bg-on-surface' : 'h-3 w-3')}
        />
      ))}
    </div>
  )
}

/**
 * The dice cluster. Tumbles on a new roll (idle → tumble → result); honors
 * `prefers-reduced-motion` by snapping straight to the result (no tumble), per the
 * task's reduced-motion fallback. Renders 1 or 2 dice from `state.last_dice`.
 */
export function Dice({ dice }: { dice: number[] }) {
  const reduced = usePrefersReducedMotion()
  const [tumbling, setTumbling] = useState(false)
  const prev = useRef<string>('')

  useEffect(() => {
    const key = dice.join(',')
    if (key && key !== prev.current) {
      prev.current = key
      if (!reduced && dice.length > 0) {
        setTumbling(true)
        const id = window.setTimeout(() => setTumbling(false), 600)
        return () => window.clearTimeout(id)
      }
    }
  }, [dice, reduced])

  if (dice.length === 0) {
    // Idle placeholder before the first roll of a turn.
    return (
      <div className="flex gap-3" aria-hidden>
        <div className="h-16 w-16 rounded-lg border-2 border-dashed border-surface-container-lowest/40" />
      </div>
    )
  }

  return (
    <div className="flex gap-3">
      {dice.map((d, i) => (
        <DieFace key={i} value={d} tumbling={tumbling} />
      ))}
    </div>
  )
}
