'use client'

import { useLocale, useTranslations } from 'next-intl'
import { useTransition } from 'react'

import { usePathname, useRouter } from '@/i18n/navigation'
import { routing } from '@/i18n/routing'
import { cn } from '@/lib/cn'

/**
 * Locale toggle (EN ↔ RU). Switches in place via the locale-aware router — no full
 * reload, satisfying the S3.5 AC. Keeps the current path/query and only swaps the
 * locale prefix.
 */
export function LocaleSwitcher() {
  const t = useTranslations('locale')
  const locale = useLocale()
  const router = useRouter()
  const pathname = usePathname()
  const [pending, startTransition] = useTransition()

  return (
    <div
      className="inline-flex items-center gap-1 rounded-full bg-surface-container p-1 shadow-felt"
      role="group"
      aria-label={t('switch')}
    >
      {routing.locales.map((loc) => {
        const selected = loc === locale
        return (
          <button
            key={loc}
            type="button"
            aria-pressed={selected}
            disabled={pending || selected}
            onClick={() =>
              startTransition(() => {
                router.replace(pathname, { locale: loc })
              })
            }
            className={cn(
              'rounded-full px-3 py-1 font-label text-sm font-medium transition-colors',
              selected
                ? 'bg-primary-container text-on-primary-container shadow-card-press'
                : 'text-on-surface-variant hover:bg-surface-container-high',
            )}
          >
            {t(loc)}
          </button>
        )
      })}
    </div>
  )
}
