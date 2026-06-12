'use client'

import { forwardRef } from 'react'
import type { ButtonHTMLAttributes, ReactNode } from 'react'

import { cn } from '@/lib/cn'

// ── Types ─────────────────────────────────────────────────────────────────────
type Variant = 'primary' | 'secondary' | 'ghost' | 'danger'
type Size = 'sm' | 'md' | 'lg'

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant
  size?: Size
  /** Optional leading icon/glyph (already sized by the caller). */
  leading?: ReactNode
  fullWidth?: boolean
}

// ── Constants ──────────────────────────────────────────────────────────────────
// "Token press": physical-token feel. A darker bottom border gives 3D depth; on
// :active the button translates 1px down and the shadow shrinks (DESIGN.md Buttons).
// `border-b-[3px]` is the depth edge; active:translate-y + active:border-b reduce it.
const BASE =
  'inline-flex items-center justify-center gap-2 font-label font-medium rounded-lg ' +
  'select-none transition-[transform,box-shadow,background-color] duration-100 ' +
  'active:translate-y-px disabled:opacity-50 disabled:pointer-events-none ' +
  'focus-visible:outline-3'

const VARIANTS: Record<Variant, string> = {
  // Gold token — the primary "Buy"/"Create" action. The depth edge reuses the
  // dark-gold on-primary-container token (no stray hex).
  primary:
    'bg-primary-container text-on-primary-container border-b-[3px] border-on-primary-container ' +
    'shadow-card hover:shadow-card-hover active:shadow-card-press active:border-b active:mt-0.5',
  // Felt green — secondary confirmations; edge = the dark felt token.
  secondary:
    'bg-secondary text-on-secondary border-b-[3px] border-on-secondary-fixed-variant ' +
    'shadow-card hover:shadow-card-hover active:shadow-card-press active:border-b active:mt-0.5',
  // Quiet, no token depth — tertiary/cancel.
  ghost:
    'bg-transparent text-on-surface-variant border-b-[3px] border-transparent ' +
    'hover:bg-surface-container active:bg-surface-container-high',
  // Destructive (kick/leave); edge = the dark error token.
  danger:
    'bg-error-container text-on-error-container border-b-[3px] border-on-error-container ' +
    'shadow-card hover:shadow-card-hover active:shadow-card-press active:border-b active:mt-0.5',
}

const SIZES: Record<Size, string> = {
  sm: 'h-9 px-3 text-sm',
  md: 'h-11 px-5 text-base',
  lg: 'h-14 px-7 text-lg',
}

// ── Component ───────────────────────────────────────────────────────────────────
export const Button = forwardRef<HTMLButtonElement, ButtonProps>(function Button(
  { variant = 'primary', size = 'md', leading, fullWidth, className, children, type, ...rest },
  ref,
) {
  return (
    <button
      ref={ref}
      type={type ?? 'button'}
      className={cn(
        BASE,
        VARIANTS[variant],
        SIZES[size],
        fullWidth && 'w-full',
        className,
      )}
      {...rest}
    >
      {leading}
      {children}
    </button>
  )
})
