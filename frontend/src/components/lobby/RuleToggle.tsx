'use client'

import type { ReactNode } from 'react'

import { cn } from '@/lib/cn'

interface RuleToggleProps {
  checked: boolean
  onChange: (next: boolean) => void
  label: string
  hint: string
  glyph?: ReactNode
}

/**
 * A card-style checkbox for an optional game mode (+Millionaire's Row, 10-Card
 * Market). Rendered as a real checkbox for a11y, styled as a selectable tile that
 * lights up gold when enabled.
 */
export function RuleToggle({ checked, onChange, label, hint, glyph }: RuleToggleProps) {
  return (
    <label
      className={cn(
        'flex cursor-pointer items-start gap-3 rounded-lg border-2 p-3 transition-colors',
        checked
          ? 'border-primary bg-primary-container/25'
          : 'border-outline-variant bg-surface-container-low hover:border-outline',
      )}
    >
      <input
        type="checkbox"
        checked={checked}
        onChange={(e) => onChange(e.target.checked)}
        className="sr-only"
      />
      <span
        className={cn(
          'mt-0.5 grid h-5 w-5 shrink-0 place-items-center rounded-DEFAULT border-2 text-xs',
          checked
            ? 'border-primary bg-primary text-on-primary'
            : 'border-outline bg-surface-container-lowest',
        )}
        aria-hidden
      >
        {checked ? '✓' : ''}
      </span>
      <span className="min-w-0">
        <span className="flex items-center gap-1 font-label text-sm font-medium text-on-surface">
          {glyph && <span aria-hidden>{glyph}</span>}
          {label}
        </span>
        <span className="block font-body text-xs text-on-surface-variant">{hint}</span>
      </span>
    </label>
  )
}
