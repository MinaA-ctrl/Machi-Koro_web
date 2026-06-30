'use client'

import { useQuery, useQueryClient } from '@tanstack/react-query'
import { useLocale, useTranslations } from 'next-intl'
import { useState } from 'react'

import { ApiError, api } from '@/lib/api'
import { clearTokens } from '@/lib/tokens'
import type { UserOut } from '@/types/api'
import { Button, Modal, useToast } from '@/components/ui'

const INPUT =
  'w-full rounded-DEFAULT bg-surface-container-low px-3 py-2.5 font-body text-body-md ' +
  'text-on-surface placeholder:text-on-surface-variant/60 border-2 border-secondary-fixed-dim ' +
  'shadow-felt focus:border-secondary focus:outline-none'

/**
 * Account dialog opened from the header avatar. For a guest (or signed-out) it shows
 * Sign in / Register (toggle); for a registered account it shows the profile + Log
 * out. All auth round-trips to the Stage-2 backend; tokens are stored by the api
 * client and ['me'] is invalidated so the header reflects the new state.
 */
export function AuthModal({
  open,
  onClose,
  account,
}: {
  open: boolean
  onClose: () => void
  account: UserOut | undefined
}) {
  const t = useTranslations('auth')
  const tt = useTranslations('toast')
  const locale = useLocale()
  const qc = useQueryClient()
  const { show } = useToast()
  const registered = account?.kind === 'registered'

  // Lifetime point total for the signed-in player (account view only).
  const { data: stats } = useQuery({
    queryKey: ['myStats'],
    queryFn: () => api.myStats(),
    enabled: open && registered,
    staleTime: 30_000,
  })

  const [mode, setMode] = useState<'login' | 'register'>('login')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [name, setName] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  // True when registration failed because the email already has an account — we then
  // offer a one-tap switch to the log-in form (email stays prefilled).
  const [emailExists, setEmailExists] = useState(false)

  function reset() {
    setEmail('')
    setPassword('')
    setName('')
    setError(null)
    setEmailExists(false)
  }

  function switchMode(next: 'login' | 'register') {
    setMode(next)
    setError(null)
    setEmailExists(false)
  }

  function close() {
    reset()
    onClose()
  }

  async function submit() {
    if (busy || !email.trim() || !password) return
    setBusy(true)
    setError(null)
    setEmailExists(false)
    try {
      if (mode === 'register') {
        await api.register({
          email: email.trim(),
          password,
          display_name: name.trim() || null,
          language: locale,
        })
      } else {
        await api.login({ email: email.trim(), password })
      }
      await qc.invalidateQueries({ queryKey: ['me'] })
      show(t(mode === 'register' ? 'registered' : 'loggedIn'), 'success')
      close()
    } catch (err) {
      if (err instanceof ApiError && err.status === 409) {
        // The backend distinguishes a clashing display name from a taken email; the
        // latter offers a jump to log in (the account already exists).
        const nameTaken = err.detail === 'name_taken'
        setError(nameTaken ? t('nameTaken') : t('emailExists'))
        setEmailExists(!nameTaken)
      } else if (err instanceof ApiError && err.status === 401) setError(t('badCredentials'))
      else setError(tt('networkError'))
    } finally {
      setBusy(false)
    }
  }

  async function logout() {
    clearTokens()
    // Re-mint a guest so the lobby keeps working without an explicit sign-in.
    try {
      await api.guest({ language: locale })
    } catch {
      /* a later action will surface a network toast */
    }
    await qc.invalidateQueries({ queryKey: ['me'] })
    show(t('loggedOut'), 'info')
    onClose()
  }

  // ── Signed-in (registered) view ───────────────────────────────────────────
  if (registered && account) {
    return (
      <Modal
        open={open}
        onClose={onClose}
        title={t('accountTitle')}
        actions={
          <>
            <Button variant="ghost" onClick={onClose}>
              {t('close')}
            </Button>
            <Button variant="primary" onClick={logout}>
              {t('logout')}
            </Button>
          </>
        }
      >
        <p className="font-body text-body-md text-on-surface">
          {t('signedInAs', { name: account.display_name })}
        </p>
        {account.email && (
          <p className="mt-1 font-body text-sm text-on-surface-variant">{account.email}</p>
        )}
        <div className="mt-4 flex items-center justify-between rounded-lg bg-surface-container-low px-3 py-2.5">
          <span className="font-label text-sm text-on-surface-variant">{t('totalPoints')}</span>
          <span className="font-number text-body-lg font-bold text-primary">
            {stats?.total_points ?? 0}
          </span>
        </div>
        {stats != null && stats.games_played > 0 && (
          <p className="mt-1.5 text-right font-body text-xs text-on-surface-variant">
            {t('gamesSummary', { played: stats.games_played, won: stats.games_won })}
          </p>
        )}
      </Modal>
    )
  }

  // ── Sign in / Register view ───────────────────────────────────────────────
  return (
    <Modal
      open={open}
      onClose={close}
      title={mode === 'login' ? t('signIn') : t('createAccount')}
      actions={
        <>
          <Button variant="ghost" onClick={close}>
            {t('cancel')}
          </Button>
          <Button variant="primary" disabled={busy || !email.trim() || !password} onClick={submit}>
            {mode === 'login' ? t('signIn') : t('register')}
          </Button>
        </>
      }
    >
      <div className="space-y-3">
        {mode === 'register' && (
          <input
            type="text"
            value={name}
            maxLength={20}
            onChange={(e) => setName(e.target.value)}
            placeholder={t('namePlaceholder')}
            aria-label={t('displayName')}
            className={INPUT}
          />
        )}
        <input
          type="email"
          value={email}
          autoComplete="email"
          onChange={(e) => setEmail(e.target.value)}
          placeholder={t('emailPlaceholder')}
          aria-label={t('email')}
          className={INPUT}
        />
        <input
          type="password"
          value={password}
          autoComplete={mode === 'login' ? 'current-password' : 'new-password'}
          onChange={(e) => setPassword(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && submit()}
          placeholder={t('passwordPlaceholder')}
          aria-label={t('password')}
          className={INPUT}
        />
        {error && (
          <div className="space-y-1">
            <p className="font-body text-sm text-error">{error}</p>
            {emailExists && (
              <button
                type="button"
                className="font-label text-sm font-medium text-primary underline-offset-2 hover:underline"
                onClick={() => switchMode('login')}
              >
                {t('goToLogin')}
              </button>
            )}
          </div>
        )}
        <button
          type="button"
          className="font-label text-sm text-primary underline-offset-2 hover:underline"
          onClick={() => switchMode(mode === 'login' ? 'register' : 'login')}
        >
          {mode === 'login' ? t('needAccount') : t('haveAccount')}
        </button>
      </div>
    </Modal>
  )
}
