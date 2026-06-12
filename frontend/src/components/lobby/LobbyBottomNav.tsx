'use client'

import { useTranslations } from 'next-intl'

import { cn } from '@/lib/cn'

const ITEMS = [
  { key: 'market', glyph: '🛒' },
  { key: 'city', glyph: '🏙️' },
  { key: 'trade', glyph: '🤝' },
  { key: 'milestones', glyph: '🏆' },
] as const

/**
 * Bottom navigation rail from the lobby design. Purely presentational here (the
 * lobby has one active section); the board reuses the pattern for real sections.
 */
export function LobbyBottomNav() {
  const t = useTranslations('nav')
  return (
    <nav className="fixed inset-x-0 bottom-0 z-40 border-t border-outline-variant bg-surface-container/95 backdrop-blur">
      <ul className="mx-auto flex max-w-5xl items-stretch justify-around px-4">
        {ITEMS.map((item, i) => {
          const active = item.key === 'city'
          return (
            <li key={item.key} className="flex-1">
              <button
                type="button"
                aria-current={active ? 'page' : undefined}
                className={cn(
                  'flex w-full flex-col items-center gap-0.5 py-2 font-label text-xs',
                  active ? 'text-primary' : 'text-on-surface-variant',
                )}
              >
                <span
                  className={cn(
                    'grid h-10 w-10 place-items-center rounded-full text-lg',
                    active && 'bg-primary-container text-on-primary-container shadow-card',
                  )}
                  aria-hidden
                >
                  {item.glyph}
                </span>
                {t(item.key)}
              </button>
            </li>
          )
        })}
      </ul>
    </nav>
  )
}
