import { forwardRef } from 'react'
import type { HTMLAttributes } from 'react'

import { cn } from '@/lib/cn'

type Elevation = 'flat' | 'card' | 'float'

interface PaperCardProps extends HTMLAttributes<HTMLDivElement> {
  /** Visual height. `card` = Level 2 paper; `float` = Level 3 (modal/die height). */
  elevation?: Elevation
  /** Add the subtle paper-grain texture overlay (cream cards). */
  grain?: boolean
  /** Add the 1px top paper-thickness highlight. */
  edge?: boolean
}

const ELEVATIONS: Record<Elevation, string> = {
  flat: 'shadow-none',
  card: 'shadow-card',
  float: 'shadow-float',
}

/**
 * Cream "paper" surface — the base of cards, panels and modals. Cream background
 * (surface-container-lowest), rounded-lg, optional grain + top edge highlight per
 * DESIGN.md Cards/Shapes.
 */
export const PaperCard = forwardRef<HTMLDivElement, PaperCardProps>(function PaperCard(
  { elevation = 'card', grain = true, edge = true, className, children, ...rest },
  ref,
) {
  return (
    <div
      ref={ref}
      className={cn(
        'relative rounded-lg bg-surface-container-lowest text-on-surface',
        ELEVATIONS[elevation],
        grain && 'paper-grain',
        edge && 'paper-edge',
        className,
      )}
      {...rest}
    >
      {children}
    </div>
  )
})
