'use client'

import { useQuery } from '@tanstack/react-query'
import { useTranslations } from 'next-intl'

import { useRouter } from '@/i18n/navigation'
import { ApiError, api } from '@/lib/api'
import { setMembership } from '@/lib/membership'
import { useEnsureAuth } from '@/lib/use-ensure-auth'
import type { TableListItem } from '@/types/api'
import { Button, PaperCard, useToast } from '@/components/ui'

/**
 * Public-table browser. Lists open, waiting tables from `GET /tables` (the backend
 * already hides protected/stale ones from the public list per its lobby rules) and
 * joins on click. Protected tables route through the waiting-room password modal.
 */
export function BrowseTables() {
  const t = useTranslations('browse')
  const tt = useTranslations('toast')
  const router = useRouter()
  const { show } = useToast()
  useEnsureAuth()

  const { data, isLoading, refetch, isFetching } = useQuery({
    queryKey: ['tables'],
    queryFn: () => api.listTables(),
    refetchInterval: 5000,
  })

  async function join(table: TableListItem) {
    try {
      if (table.is_protected) {
        // Defer to the waiting room's password modal.
        router.push(`/table/${table.code}`)
        return
      }
      const resp = await api.joinTable(table.code, {})
      setMembership({
        code: table.code,
        seat: resp.seat,
        wsToken: resp.token,
        isHost: resp.seat === 0,
      })
      router.push(`/table/${table.code}`)
    } catch (err) {
      show(err instanceof ApiError ? err.message : tt('networkError'), 'error')
    }
  }

  const tables = data ?? []

  return (
    <div>
      <div className="mb-5 flex items-end justify-between">
        <div>
          <h1 className="font-heading text-headline-lg text-on-surface">{t('title')}</h1>
          <p className="font-body text-body-md text-on-surface-variant">{t('subtitle')}</p>
        </div>
        <Button variant="ghost" size="sm" onClick={() => refetch()} disabled={isFetching}>
          {t('refresh')}
        </Button>
      </div>

      {isLoading ? (
        <p className="font-body text-on-surface-variant">…</p>
      ) : tables.length === 0 ? (
        <PaperCard className="p-8 text-center">
          <p className="font-body text-body-lg text-on-surface-variant">{t('empty')}</p>
          <Button className="mt-4" onClick={() => router.push('/')}>
            {t('refresh')}
          </Button>
        </PaperCard>
      ) : (
        <ul className="space-y-3">
          {tables.map((table) => (
            <li key={table.code}>
              <PaperCard className="flex items-center gap-4 p-4">
                <div className="min-w-0 flex-1">
                  <p className="truncate font-heading text-label-lg font-medium text-on-surface">
                    {table.name}
                  </p>
                  <div className="mt-1 flex flex-wrap items-center gap-2 font-body text-sm text-on-surface-variant">
                    <Badge>{t('version', { version: table.game_version })}</Badge>
                    {table.sharp && <Badge>💎 MR</Badge>}
                    {table.variable_supply && <Badge>🃏 10</Badge>}
                    {table.is_protected && <Badge>🔒 {t('protected')}</Badge>}
                    <span>{t('players', { count: table.player_count })}</span>
                  </div>
                </div>
                <Button
                  variant="secondary"
                  disabled={table.player_count >= 4}
                  onClick={() => join(table)}
                >
                  {t('joinTable')}
                </Button>
              </PaperCard>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}

function Badge({ children }: { children: React.ReactNode }) {
  return (
    <span className="rounded-full bg-surface-container px-2 py-0.5 font-label text-xs text-on-surface-variant">
      {children}
    </span>
  )
}
