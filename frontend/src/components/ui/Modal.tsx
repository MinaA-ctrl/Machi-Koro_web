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
  /** Render an ✕ close button in the top-right corner. */
  showClose?: boolean
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
  showClose = false,
  className,
}: ModalProps) {
  const dialogRef = useRef<HTMLDivElement>(null)
  const titleId = useId()

  // Keep the latest handlers in refs so the focus effect can depend on `open`
  // alone. If it depended on `onClose`/`dismissable` (often inline arrows), every
  // parent re-render — e.g. typing in an input inside the modal — would re-run it
  // and `root.focus()` would steal the caret back out of the field on each keystroke.
  const onCloseRef = useRef(onClose)
  onCloseRef.current = onClose
  const dismissableRef = useRef(dismissable)
  dismissableRef.current = dismissable

  // Lock scroll + move focus in once when opened; restore focus on close.
  useEffect(() => {
    if (!open) return
    const previouslyFocused = document.activeElement as HTMLElement | null
    const root = dialogRef.current
    root?.focus()

    const onKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && dismissableRef.current) {
        e.stopPropagation()
        onCloseRef.current?.()
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
    // Intentionally keyed on `open` only — dismissable/onClose are read via refs so
    // re-renders (e.g. typing inside the modal) don't re-trigger focus-in.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open])

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
        {showClose && onClose && (
          <button
            type="button"
            onClick={onClose}
            aria-label="Close"
            className="absolute right-3 top-3 grid h-8 w-8 place-items-center rounded-full text-on-surface-variant transition-colors hover:bg-surface-container hover:text-on-surface focus:outline-none focus-visible:ring-2 focus-visible:ring-primary"
          >
            <span aria-hidden className="text-lg leading-none">
              ✕
            </span>
          </button>
        )}
        {title && (
          <h2 id={titleId} className="mb-3 pr-8 font-heading text-headline-md text-on-surface">
            {title}
          </h2>
        )}
        <div className="font-body text-body-md text-on-surface-variant">{children}</div>
        {actions && <div className="mt-6 flex justify-end gap-3">{actions}</div>}
      </PaperCard>
    </div>
  )
}
