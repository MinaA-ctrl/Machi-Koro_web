'use client'

import { useLocale } from 'next-intl'
import { useEffect, useRef, useState } from 'react'

import { api } from './api'
import { getAccessToken } from './tokens'

/**
 * Guest bootstrap. If there is no stored access token, mint a guest one against
 * `/auth/guest` so the lobby can immediately create/join tables. A registered
 * session (already-stored token) is left untouched. Returns `ready` once a token
 * exists. The optional display name seeds the guest's name.
 */
export function useEnsureAuth(displayName?: string): { ready: boolean } {
  const locale = useLocale()
  const [ready, setReady] = useState(() => getAccessToken() != null)
  const started = useRef(false)

  useEffect(() => {
    if (ready || started.current) return
    started.current = true
    api
      .guest({ display_name: displayName ?? null, language: locale })
      .then(() => setReady(true))
      .catch(() => {
        // Leave not-ready; the caller surfaces a network toast on the first action.
        started.current = false
      })
  }, [ready, displayName, locale])

  return { ready }
}
