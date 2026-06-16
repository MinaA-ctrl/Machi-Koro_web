'use client'

import { useQueryClient } from '@tanstack/react-query'
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

  const [mode, setMode] = useState<'login' | 'register'>('login')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [name, setName] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  function reset() {
    setEmail('')
    setPassword('')
    setName('')
    setError(null)
  }

  function close() {
    reset()
    onClose()
  }

  async function submit() {
    if (busy || !email.trim() || !password) return
    setBusy(true)
    setError(null)
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
      if (err instanceof ApiError && err.status === 409) setError(t('emailTaken'))
      else if (err instanceof ApiError && err.status === 401) setError(t('badCredentials'))
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
            maxLength={32}
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
        {error && <p className="font-body text-sm text-error">{error}</p>}
        <button
          type="button"
          className="font-label text-sm text-primary underline-offset-2 hover:underline"
          onClick={() => {
            setMode(mode === 'login' ? 'register' : 'login')
            setError(null)
          }}
        >
          {mode === 'login' ? t('needAccount') : t('haveAccount')}
        </button>
      </div>
    </Modal>
  )
}
