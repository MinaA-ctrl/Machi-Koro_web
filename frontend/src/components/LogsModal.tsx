'use client'

import { useQuery } from '@tanstack/react-query'
import { useFormatter, useTranslations } from 'next-intl'

import { api } from '@/lib/api'
import type { UserOut } from '@/types/api'
import { Button, Modal } from '@/components/ui'

/**
 * Game-history ("Logs") dialog opened from the header. For a registered player it
 * lists their finished games (date, place, version) newest-first; guests are
 * prompted to sign in. Only games they were present at the end of are recorded.
 */
export function LogsModal({
  open,
  onClose,
  account,
}: {
  open: boolean
  onClose: () => void
  account: UserOut | undefined
}) {
  const t = useTranslations('logs')
  const f = useFormatter()
  const registered = account?.kind === 'registered'

  const { data, isLoading } = useQuery({
    queryKey: ['history'],
    queryFn: () => api.history(),
    enabled: open && registered,
    staleTime: 30_000,
  })

  const versionLabel = (v: string) =>
    v === 'harbour' ? t('versionHarbour') : t('versionBasic')

  return (
    <Modal
      open={open}
      onClose={onClose}
      title={t('title')}
      actions={<Button onClick={onClose}>{t('close')}</Button>}
    >
      {!registered ? (
        <p className="font-body text-body-md text-on-surface-variant">{t('signInPrompt')}</p>
      ) : isLoading ? (
        <p className="font-body text-on-surface-variant">…</p>
      ) : !data || data.length === 0 ? (
        <p className="font-body text-body-md text-on-surface-variant">{t('empty')}</p>
      ) : (
        <ul className="max-h-96 space-y-2 overflow-y-auto">
          {data.map((h, i) => (
            <li
              key={i}
              className="flex items-center justify-between gap-3 rounded-lg bg-surface-container-low p-3"
            >
              <div className="min-w-0">
                <p className="font-label text-on-surface">
                  {h.won && <span aria-hidden>🏆 </span>}
                  {h.place != null && h.total_players != null
                    ? t('placeOf', { place: h.place, total: h.total_players })
                    : '—'}
                </p>
                <p className="font-body text-sm text-on-surface-variant">
                  {f.dateTime(new Date(h.played_at), { dateStyle: 'medium', timeStyle: 'short' })}
                  {' · '}
                  {versionLabel(h.game_version)}
                </p>
              </div>
              <span className="shrink-0 font-number text-sm text-on-surface-variant">
                🏛 {h.landmarks_built} · 🪙 {h.coins_at_end}
              </span>
            </li>
          ))}
        </ul>
      )}
    </Modal>
  )
}
