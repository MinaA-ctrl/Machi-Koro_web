import { cn } from '@/lib/cn'

type Size = 'sm' | 'md' | 'lg'

interface CoinChipProps {
  /** Coin amount to display. */
  value: number
  size?: Size
  /** Show a leading "+"/"−" sign (for transaction deltas). */
  signed?: boolean
  className?: string
  /** Accessible label override; defaults to "<value> coins". */
  ariaLabel?: string
}

const SIZES: Record<Size, { box: string; text: string }> = {
  sm: { box: 'h-6 min-w-6 px-1.5', text: 'text-sm' },
  md: { box: 'h-8 min-w-8 px-2', text: 'text-base' },
  lg: { box: 'h-11 min-w-11 px-3', text: 'text-number-xl' },
}

/**
 * Currency chip — circular/pill gold badge with a coin emboss (DESIGN.md Chips).
 * The emboss is a soft inner highlight + lower shadow; numbers use Fredoka tabular
 * figures so counts don't reflow as they tick. AA: dark gold ink on gold.
 */
export function CoinChip({ value, size = 'md', signed, className, ariaLabel }: CoinChipProps) {
  const s = SIZES[size]
  const display = signed && value > 0 ? `+${value}` : String(value)
  return (
    <span
      className={cn(
        'inline-flex items-center justify-center rounded-full font-number font-bold tabular',
        'bg-family-gold text-on-primary-container shadow-coin-emboss',
        s.box,
        s.text,
        className,
      )}
      role="img"
      aria-label={ariaLabel ?? `${value} coins`}
    >
      {display}
    </span>
  )
}
