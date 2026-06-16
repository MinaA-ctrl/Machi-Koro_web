'use client'

import { useTranslations } from 'next-intl'
import { useState } from 'react'

import { Link } from '@/i18n/navigation'
import { useAccount } from '@/lib/use-account'
import { AuthModal } from './auth/AuthModal'
import { LocaleSwitcher } from './LocaleSwitcher'
import { LogsModal } from './LogsModal'

/**
 * Top wordmark bar shared by the lobby surfaces. The "Machi Koro" wordmark uses
 * Fredoka in the gold primary; right side carries the locale toggle, a logs
 * placeholder, and the account avatar — which opens the sign-in / register dialog
 * (or the profile + log out when already signed in).
 */
export function AppHeader() {
  const t = useTranslations('nav')
  const [authOpen, setAuthOpen] = useState(false)
  const [logsOpen, setLogsOpen] = useState(false)
  const { data: account } = useAccount()
  const registered = account?.kind === 'registered'

  return (
    <header className="flex items-center justify-between px-container-padding py-4">
      <Link
        href="/"
        className="font-display text-headline-lg font-semibold text-primary-container drop-shadow-[0_1px_0_rgba(98,72,0,0.35)]"
      >
        Machi&nbsp;Koro
      </Link>
      <div className="flex items-center gap-3">
        <LocaleSwitcher />
        <nav className="hidden items-center gap-4 font-label text-sm text-on-surface-variant sm:flex">
          <button type="button" className="hover:text-on-surface" onClick={() => setLogsOpen(true)}>
            {t('logs')}
          </button>
          {registered && account && (
            <span className="font-label text-sm text-on-surface">{account.display_name}</span>
          )}
          <button
            type="button"
            aria-label={t('account')}
            onClick={() => setAuthOpen(true)}
            className="grid h-9 w-9 place-items-center rounded-full bg-surface-container shadow-card transition-transform hover:scale-105"
          >
            <span aria-hidden>👤</span>
          </button>
        </nav>
      </div>

      <AuthModal open={authOpen} onClose={() => setAuthOpen(false)} account={account} />
      <LogsModal open={logsOpen} onClose={() => setLogsOpen(false)} account={account} />
    </header>
  )
}
