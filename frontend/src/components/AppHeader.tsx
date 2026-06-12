'use client'

import { useTranslations } from 'next-intl'

import { Link } from '@/i18n/navigation'
import { LocaleSwitcher } from './LocaleSwitcher'

/**
 * Top wordmark bar shared by the lobby surfaces. The "Machi Koro" wordmark uses
 * Fredoka in the gold primary; right side carries the locale toggle + quiet
 * account/log affordances (wired in later phases).
 */
export function AppHeader() {
  const t = useTranslations('nav')
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
          <button type="button" className="hover:text-on-surface">
            {t('store')}
          </button>
          <button type="button" className="hover:text-on-surface">
            {t('logs')}
          </button>
          <button
            type="button"
            aria-label={t('account')}
            className="grid h-9 w-9 place-items-center rounded-full bg-surface-container shadow-card"
          >
            <span aria-hidden>👤</span>
          </button>
        </nav>
      </div>
    </header>
  )
}
