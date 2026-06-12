'use client'

import { useEffect, useState } from 'react'

/**
 * Reads `prefers-reduced-motion: reduce` reactively. Components use this where the
 * difference between motion and stillness is *structural* (e.g. a dice tumble vs.
 * an instant snap to the result) rather than purely cosmetic — cosmetic cases are
 * already neutralized globally in globals.css.
 *
 * SSR-safe: starts `false`, syncs on mount, and updates if the user toggles the OS
 * setting mid-session.
 */
export function usePrefersReducedMotion(): boolean {
  const [reduced, setReduced] = useState(false)

  useEffect(() => {
    const mq = window.matchMedia('(prefers-reduced-motion: reduce)')
    setReduced(mq.matches)
    const onChange = (e: MediaQueryListEvent) => setReduced(e.matches)
    mq.addEventListener('change', onChange)
    return () => mq.removeEventListener('change', onChange)
  }, [])

  return reduced
}
