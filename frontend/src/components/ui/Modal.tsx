'use client'

import { useEffect, useId, useRef } from 'react'
import type { ReactNode } from 'react'

import { cn } from '@/lib/cn'
import { PaperCard } from './PaperCard'

interface ModalProps {
  open: boolean
  onClose?: () => void
  title?: ReactNode
  children: ReactNode
  /** Footer action row. */
  actions?: ReactNode
  /** Disable closing on backdrop click / Escape (for blocking overlays). */
  dismissable?: boolean
  className?: string
}

/**
 * Premium-card modal over a 5px backdrop blur (DESIGN.md Modals). Accessible:
 * role="dialog" + aria-modal, labelled by the title, Escape to dismiss, focus
 * moved into the dialog on open and a basic focus trap on Tab. The dialog body is
 * a PaperCard at Level 3 (float) elevation.
 */
export function Modal({
  open,
  onClose,
  title,
  children,
  actions,
  dismissable = true,
  className,
}: ModalProps) {
  const dialogRef = useRef<HTMLDivElement>(null)
  const titleId = useId()

  // Lock scroll + move focus in while open; restore focus on close.
  useEffect(() => {
    if (!open) return
    const previouslyFocused = document.activeElement as HTMLElement | null
    const root = dialogRef.current
    root?.focus()

    const onKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && dismissable) {
        e.stopPropagation()
        onClose?.()
        return
      }
      if (e.key !== 'Tab' || !root) return
      const focusables = root.querySelectorAll<HTMLElement>(
        'a[href], button:not([disabled]), textarea, input, select, [tabindex]:not([tabindex="-1"])',
      )
      if (focusables.length === 0) return
      const first = focusables[0]!
      const last = focusables[focusables.length - 1]!
      if (e.shiftKey && document.activeElement === first) {
        e.preventDefault()
        last.focus()
      } else if (!e.shiftKey && document.activeElement === last) {
        e.preventDefault()
        first.focus()
      }
    }

    document.addEventListener('keydown', onKeyDown)
    const prevOverflow = document.body.style.overflow
    document.body.style.overflow = 'hidden'
    return () => {
      document.removeEventListener('keydown', onKeyDown)
      document.body.style.overflow = prevOverflow
      previouslyFocused?.focus?.()
    }
  }, [open, dismissable, onClose])

  if (!open) return null

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-container-padding"
      role="presentation"
    >
      {/* Backdrop blur keeps focus on the active board piece. */}
      <div
        className="absolute inset-0 bg-inverse-surface/40 backdrop-blur-modal animate-fade-in"
        onClick={dismissable ? onClose : undefined}
        aria-hidden="true"
      />
      <PaperCard
        ref={dialogRef}
        elevation="float"
        role="dialog"
        aria-modal="true"
        aria-labelledby={title ? titleId : undefined}
        tabIndex={-1}
        className={cn(
          'relative z-10 w-full max-w-md p-6 animate-modal-in focus:outline-none',
          className,
        )}
      >
        {title && (
          <h2 id={titleId} className="mb-3 font-heading text-headline-md text-on-surface">
            {title}
          </h2>
        )}
        <div className="font-body text-body-md text-on-surface-variant">{children}</div>
        {actions && <div className="mt-6 flex justify-end gap-3">{actions}</div>}
      </PaperCard>
    </div>
  )
}
