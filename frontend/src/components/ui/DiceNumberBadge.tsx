import { cn } from '@/lib/cn'

interface DiceNumberBadgeProps {
  /** The single activation number, or a [min,max] range for multi-roll cards. */
  value: number | [number, number]
  /** Dim the badge when this card won't activate on the current roll. */
  active?: boolean
  className?: string
}

/**
 * The small "activation number" circle at the top of a card — styled like
 * high-quality printed ink (DESIGN.md Chips & Badges → Activation Numbers).
 * Fredoka, ink-brown on cream, with a thin printed ring.
 */
export function DiceNumberBadge({ value, active = true, className }: DiceNumberBadgeProps) {
  const label = Array.isArray(value) ? `${value[0]}–${value[1]}` : String(value)
  return (
    <span
      className={cn(
        'inline-flex h-7 min-w-7 items-center justify-center rounded-full px-1.5',
        'bg-surface-container-lowest font-number text-sm font-bold tabular',
        'ring-2 ring-on-surface/80 text-on-surface',
        !active && 'opacity-35',
        className,
      )}
      aria-label={`Activates on ${label}`}
    >
      {label}
    </span>
  )
}
