'use client'

import { useTranslations } from 'next-intl'

import { PaperCard } from '@/components/ui'

/**
 * Placeholder for the cosmetics shop ("Market" tab) — themes/avatars to customize
 * the game, planned for a later stage. For now it just announces "coming soon".
 */
export function MarketComingSoon() {
  const t = useTranslations('marketPage')
  return (
    <div className="flex flex-1 items-center justify-center">
      <PaperCard className="w-full max-w-xl p-10 text-center">
        <div className="text-5xl" aria-hidden>
          🛍️
        </div>
        <h1 className="mt-4 font-heading text-headline-lg text-on-surface">{t('title')}</h1>
        <p className="mt-2 font-heading text-headline-md text-primary">{t('comingSoon')}</p>
        <p className="mt-3 font-body text-body-md text-on-surface-variant">{t('subtitle')}</p>
      </PaperCard>
    </div>
  )
}
