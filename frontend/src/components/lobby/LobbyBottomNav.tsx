'use client'

import { useTranslations } from 'next-intl'

import { usePathname, useRouter } from '@/i18n/navigation'
import { cn } from '@/lib/cn'

const ITEMS = [
  { key: 'market', glyph: '🛒', href: '/market' },
  { key: 'city', glyph: '🏙️', href: '/' },
  { key: 'rules', glyph: '📖', href: '/rules' },
  { key: 'milestones', glyph: '🏆', href: null },
] as const

/**
 * Bottom navigation rail from the lobby design. Rules routes to the rules page;
 * the other tabs are presentational placeholders for now (the lobby is one view).
 */
export function LobbyBottomNav() {
  const t = useTranslations('nav')
  const router = useRouter()
  const pathname = usePathname()

  return (
    <nav className="fixed inset-x-0 bottom-0 z-40 border-t border-outline-variant bg-surface-container/95 backdrop-blur">
      <ul className="mx-auto flex max-w-5xl items-stretch justify-around px-4">
        {ITEMS.map((item) => {
          const active =
            (item.key === 'rules' && pathname === '/rules') ||
            (item.key === 'market' && pathname === '/market') ||
            (item.key === 'city' && pathname === '/')
          return (
            <li key={item.key} className="flex-1">
              <button
                type="button"
                aria-current={active ? 'page' : undefined}
                onClick={item.href ? () => router.push(item.href!) : undefined}
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
