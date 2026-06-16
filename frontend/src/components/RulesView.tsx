'use client'

import { useLocale, useTranslations } from 'next-intl'
import { useState } from 'react'

import { Link } from '@/i18n/navigation'
import { RULES } from '@/lib/rules-content'
import type { RuleSet } from '@/lib/rules-content'
import { cn } from '@/lib/cn'
import { Button, PaperCard } from '@/components/ui'

/**
 * The rules reference: a tab per rule set (Basic, Harbour, Millionaire's Row,
 * 10-card market). Content is localized in rules-content.ts and chosen by the
 * active locale; this component is purely presentational.
 */
export function RulesView() {
  const locale = useLocale()
  const t = useTranslations('rulesPage')
  const sets: RuleSet[] = RULES[locale] ?? RULES.en
  const [activeId, setActiveId] = useState(sets[0]!.id)
  const current = sets.find((s) => s.id === activeId) ?? sets[0]!

  return (
    <div className="mx-auto w-full max-w-3xl">
      <div className="mb-4 flex items-center justify-between gap-3">
        <h1 className="font-heading text-headline-lg text-on-surface">{t('title')}</h1>
        <Link href="/">
          <Button variant="ghost" size="sm">
            ← {t('back')}
          </Button>
        </Link>
      </div>
      <p className="mb-5 font-body text-body-md text-on-surface-variant">{t('subtitle')}</p>

      {/* Rule-set tabs */}
      <div role="tablist" aria-label={t('title')} className="mb-4 flex flex-wrap gap-2">
        {sets.map((s) => (
          <button
            key={s.id}
            type="button"
            role="tab"
            aria-selected={s.id === activeId}
            onClick={() => setActiveId(s.id)}
            className={cn(
              'rounded-full px-4 py-2 font-label text-sm font-medium transition-colors',
              s.id === activeId
                ? 'bg-primary text-on-primary shadow-card'
                : 'bg-surface-container text-on-surface-variant hover:bg-surface-container-high',
            )}
          >
            {s.title}
          </button>
        ))}
      </div>

      <PaperCard className="p-6">
        <h2 className="font-heading text-headline-md text-on-surface">{current.title}</h2>
        <p className="mt-1 font-body text-body-md text-on-surface-variant">{current.blurb}</p>

        <div className="mt-5 space-y-5">
          {current.blocks.map((block) => (
            <section key={block.heading}>
              <h3 className="mb-2 font-label text-sm font-semibold uppercase tracking-wide text-primary">
                {block.heading}
              </h3>
              <ul className="space-y-1.5">
                {block.points.map((point, i) => (
                  <li
                    key={i}
                    className="flex gap-2 font-body text-body-md text-on-surface-variant"
                  >
                    <span aria-hidden className="mt-1 text-on-surface-variant/50">
                      •
                    </span>
                    <span>{point}</span>
                  </li>
                ))}
              </ul>
            </section>
          ))}
        </div>
      </PaperCard>
    </div>
  )
}
