'use client'

import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useRef,
  useState,
} from 'react'
import type { ReactNode } from 'react'

import { cn } from '@/lib/cn'

// ── Types ─────────────────────────────────────────────────────────────────────
type ToastTone = 'info' | 'success' | 'warning' | 'error'

interface Toast {
  id: number
  message: string
  tone: ToastTone
}

interface ToastContextValue {
  show: (message: string, tone?: ToastTone, durationMs?: number) => void
}

// ── Context ────────────────────────────────────────────────────────────────────
const ToastContext = createContext<ToastContextValue | null>(null)

export function useToast(): ToastContextValue {
  const ctx = useContext(ToastContext)
  if (!ctx) throw new Error('useToast must be used within <ToastProvider>')
  return ctx
}

const TONE_STYLES: Record<ToastTone, string> = {
  info: 'bg-inverse-surface text-inverse-on-surface',
  success: 'bg-secondary text-on-secondary',
  warning: 'bg-primary-container text-on-primary-container',
  error: 'bg-error text-on-error',
}

/**
 * Toast host. Stacks transient messages bottom-center with the cozy slide-up
 * entrance (reduced-motion neutralizes it globally). Live region announces to
 * screen readers (role="status", aria-live polite).
 */
export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([])
  const nextId = useRef(1)

  const dismiss = useCallback((id: number) => {
    setToasts((t) => t.filter((x) => x.id !== id))
  }, [])

  const show = useCallback(
    (message: string, tone: ToastTone = 'info', durationMs = 3200) => {
      const id = nextId.current++
      setToasts((t) => [...t, { id, message, tone }])
      window.setTimeout(() => dismiss(id), durationMs)
    },
    [dismiss],
  )

  const value = useMemo(() => ({ show }), [show])

  return (
    <ToastContext.Provider value={value}>
      {children}
      <div
        className="pointer-events-none fixed inset-x-0 bottom-6 z-[60] flex flex-col items-center gap-2 px-4"
        role="status"
        aria-live="polite"
      >
        {toasts.map((t) => (
          <button
            key={t.id}
            type="button"
            onClick={() => dismiss(t.id)}
            className={cn(
              'pointer-events-auto max-w-sm rounded-lg px-4 py-3 text-center font-body text-body-md shadow-float animate-toast-in',
              TONE_STYLES[t.tone],
            )}
          >
            {t.message}
          </button>
        ))}
      </div>
    </ToastContext.Provider>
  )
}
