'use client'

import { useQuery, useQueryClient } from '@tanstack/react-query'
import { useTranslations } from 'next-intl'
import { useEffect, useState } from 'react'

import { useRouter } from '@/i18n/navigation'
import { ApiError, api } from '@/lib/api'
import { cn } from '@/lib/cn'
import {
  clearMembership,
  getMembership,
  setMembership,
} from '@/lib/membership'
import type { Membership } from '@/lib/membership'
import { useLobbySocket } from '@/lib/use-lobby-socket'
import { Button, Modal, PaperCard, useToast } from '@/components/ui'

const MAX_SEATS = 5

/**
 * Waiting room — players gathering before the host starts. Reads table detail from
 * REST (polled), prompts for a password if the player arrived without joining a
 * protected table, lets the host kick + start, and routes everyone into the board
 * once the table flips to `playing`.
 *
 * NOTE (S3.2 gap): live presence currently uses a short poll. The lobby WebSocket
 * (`/ws/{code}/lobby/{seat}`) wiring for instant join/leave/kick/close is the next
 * increment; the event contract is already modeled in types/game.ts.
 */
export function WaitingRoom({ code }: { code: string }) {
  const t = useTranslations('waiting')
  const tt = useTranslations('toast')
  const tp = useTranslations('password')
  const router = useRouter()
  const { show } = useToast()
  const queryClient = useQueryClient()

  const [membership, setMembershipState] = useState<Membership | null>(null)
  const [needsPassword, setNeedsPassword] = useState(false)
  const [password, setPassword] = useState('')
  const [copied, setCopied] = useState(false)
  const [starting, setStarting] = useState(false)
  const [closed, setClosed] = useState(false)
  const [kicked, setKicked] = useState(false)
  const [renaming, setRenaming] = useState(false)
  const [renameValue, setRenameValue] = useState('')
  const [savingName, setSavingName] = useState(false)

  useEffect(() => {
    setMembershipState(getMembership(code))
  }, [code])

  const { data: table, error } = useQuery({
    queryKey: ['table', code],
    queryFn: () => api.getTable(code),
    // The lobby socket drives live presence; this slow poll is a reconnect-safety
    // net only. Stops once a terminal overlay is showing.
    refetchInterval: closed || kicked ? false : 15000,
  })

  // Live presence + terminal events over the lobby WebSocket.
  const lobby = useLobbySocket(membership ? code : null, membership?.seat ?? null, {
    onPresenceChange: () => queryClient.invalidateQueries({ queryKey: ['table', code] }),
    onTableClosed: () => setClosed(true),
    onKicked: (seat) => {
      if (membership?.seat === seat) {
        clearMembership(code)
        setKicked(true)
      } else {
        queryClient.invalidateQueries({ queryKey: ['table', code] })
      }
    },
  })

  // Protected table + not yet seated → prompt for the access key.
  useEffect(() => {
    if (table?.is_protected && !getMembership(code)) setNeedsPassword(true)
  }, [table, code])

  // Once the table starts, everyone seated moves to the board.
  useEffect(() => {
    if (table?.status === 'playing') router.push(`/game/${code}`)
  }, [table?.status, code, router])

  async function submitPassword() {
    try {
      const resp = await api.joinTable(code, { password })
      const m = { code, seat: resp.seat, wsToken: resp.token, isHost: resp.seat === 0 }
      setMembership(m)
      setMembershipState(m)
      setNeedsPassword(false)
    } catch (err) {
      show(err instanceof ApiError && err.status === 403 ? tp('wrong') : tt('networkError'), 'error')
    }
  }

  async function copyCode() {
    try {
      await navigator.clipboard.writeText(code.toUpperCase())
      setCopied(true)
      window.setTimeout(() => setCopied(false), 1500)
    } catch {
      show(tt('copyFailed'), 'warning')
    }
  }

  async function kick(seat: number) {
    try {
      await api.kick(code, seat)
      // Tell the room over the lobby socket; the carried seat lets the kicked
      // client recognize itself (app/ws.py preserves a provided `seat`).
      lobby.send({ event: 'player_kicked', seat })
      queryClient.invalidateQueries({ queryKey: ['table', code] })
    } catch (err) {
      show(err instanceof ApiError ? err.message : tt('networkError'), 'error')
    }
  }

  async function start() {
    if (starting) return
    setStarting(true)
    try {
      const resp = await api.startTable(code)
      // start re-issues the host's per-seat token.
      if (membership) {
        const m = { ...membership, wsToken: resp.token }
        setMembership(m)
        setMembershipState(m)
      }
      router.push(`/game/${code}`)
    } catch (err) {
      show(err instanceof ApiError ? err.message : tt('networkError'), 'error')
    } finally {
      setStarting(false)
    }
  }

  function leave() {
    clearMembership(code)
    router.push('/')
  }

  // Open the rename modal seeded with the player's current name.
  function openRename(currentName: string) {
    setRenameValue(currentName)
    setRenaming(true)
  }

  // Rename works for guests and registered players alike — the backend authorizes
  // by seat ownership, not account kind.
  async function submitRename() {
    if (savingName || membership == null) return
    const next = renameValue.trim()
    if (!next) return
    setSavingName(true)
    try {
      await api.rename(code, membership.seat, next)
      // Reflect it locally now; nudge the room to re-pull the roster (the lobby
      // socket's default branch treats any relayed message as a presence hint).
      queryClient.invalidateQueries({ queryKey: ['table', code] })
      lobby.send({ event: 'player_renamed', seat: membership.seat })
      setRenaming(false)
    } catch (err) {
      show(err instanceof ApiError ? err.message : tt('networkError'), 'error')
    } finally {
      setSavingName(false)
    }
  }

  const backToLobby = () => router.push('/')
  if (kicked) return <TerminalOverlay kind="kicked" onBack={backToLobby} />
  if (closed || (error instanceof ApiError && error.status === 404)) {
    return <TerminalOverlay kind="closed" onBack={backToLobby} />
  }

  const players = table?.players ?? []
  const isHost = membership?.isHost ?? false
  const canStart = isHost && players.length >= 2

  return (
    <>
      <PaperCard className="p-6">
        <h1 className="font-heading text-headline-lg text-on-surface">{t('title')}</h1>
        {table && <p className="mt-1 font-body text-body-md text-on-surface-variant">{table.name}</p>}

        {/* Table code + copy */}
        <div className="mt-4 flex items-center gap-3 rounded-lg bg-surface-container-low p-3 shadow-felt">
          <div>
            <p className="font-label text-xs uppercase tracking-wide text-on-surface-variant">
              {t('tableCode')}
            </p>
            <p className="font-number text-headline-md font-bold tracking-widest text-primary">
              {code.toUpperCase()}
            </p>
          </div>
          <Button variant="ghost" size="sm" className="ml-auto" onClick={copyCode}>
            {copied ? t('copied') : t('copyCode')}
          </Button>
        </div>

        {/* Seats */}
        <ul className="mt-5 space-y-2">
          {Array.from({ length: MAX_SEATS }).map((_, i) => {
            const p = players.find((pl) => pl.seat === i)
            const isMe = membership?.seat === i
            return (
              <li
                key={i}
                className={cn(
                  'flex items-center gap-3 rounded-lg border-2 p-3',
                  p
                    ? 'border-secondary-fixed-dim bg-surface-container-low'
                    : 'border-dashed border-outline-variant',
                )}
              >
                <span
                  className="grid h-9 w-9 place-items-center rounded-full bg-surface-container text-lg shadow-card"
                  aria-hidden
                >
                  {p ? '🧑' : '➕'}
                </span>
                <span className="font-label text-on-surface">
                  {p ? p.display_name : t('seatOpen')}
                  {isMe && <span className="ml-1 text-on-surface-variant">({t('ready')})</span>}
                </span>
                {p?.is_host && (
                  <span className="rounded-full bg-primary-container px-2 py-0.5 font-label text-xs text-on-primary-container">
                    {t('host')}
                  </span>
                )}
                {isMe && p && (
                  <Button
                    variant="ghost"
                    size="sm"
                    className="ml-auto"
                    onClick={() => openRename(p.display_name)}
                  >
                    {t('rename')}
                  </Button>
                )}
                {isHost && p && !p.is_host && (
                  <Button
                    variant="ghost"
                    size="sm"
                    className="ml-auto text-error"
                    onClick={() => kick(p.seat)}
                  >
                    {t('kick')}
                  </Button>
                )}
              </li>
            )
          })}
        </ul>

        {/* Actions */}
        <div className="mt-6 flex items-center justify-between gap-3">
          <Button variant="ghost" onClick={leave}>
            {t('leave')}
          </Button>
          {isHost ? (
            <span className="flex flex-col items-end gap-1">
              <Button variant="primary" disabled={!canStart || starting} onClick={start}>
                {t('startGame')}
              </Button>
              {!canStart && (
                <span className="font-body text-xs text-on-surface-variant">
                  {t('needMorePlayers')}
                </span>
              )}
            </span>
          ) : (
            <span className="font-body text-sm text-on-surface-variant">{t('waitingForHost')}</span>
          )}
        </div>
      </PaperCard>

      <Modal
        open={needsPassword}
        dismissable={false}
        title={tp('title')}
        actions={
          <>
            <Button variant="ghost" onClick={() => router.push('/')}>
              {t('leave')}
            </Button>
            <Button onClick={submitPassword}>{tp('submit')}</Button>
          </>
        }
      >
        <p className="mb-3">{tp('subtitle')}</p>
        <input
          type="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && submitPassword()}
          placeholder={tp('placeholder')}
          aria-label={tp('placeholder')}
          className="w-full rounded-DEFAULT border-2 border-secondary-fixed-dim bg-surface-container-low px-3 py-2.5 font-body shadow-felt focus:border-secondary focus:outline-none"
        />
      </Modal>

      <Modal
        open={renaming}
        onClose={() => setRenaming(false)}
        title={t('renameTitle')}
        actions={
          <>
            <Button variant="ghost" onClick={() => setRenaming(false)}>
              {t('renameCancel')}
            </Button>
            <Button disabled={savingName || !renameValue.trim()} onClick={submitRename}>
              {t('renameSave')}
            </Button>
          </>
        }
      >
        <input
          type="text"
          maxLength={32}
          value={renameValue}
          onChange={(e) => setRenameValue(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && submitRename()}
          placeholder={t('renamePlaceholder')}
          aria-label={t('renamePlaceholder')}
          autoFocus
          className="w-full rounded-DEFAULT border-2 border-secondary-fixed-dim bg-surface-container-low px-3 py-2.5 font-body shadow-felt focus:border-secondary focus:outline-none"
        />
      </Modal>
    </>
  )
}

/** Blocking end-state overlay for the kicked + table-closed cases. */
function TerminalOverlay({ kind, onBack }: { kind: 'kicked' | 'closed'; onBack: () => void }) {
  const t = useTranslations('overlay')
  const title = kind === 'kicked' ? t('kickedTitle') : t('closedTitle')
  const body = kind === 'kicked' ? t('kickedBody') : t('closedBody')
  return (
    <Modal
      open
      dismissable={false}
      title={title}
      actions={<Button onClick={onBack}>{t('backToLobby')}</Button>}
    >
      <p>{body}</p>
    </Modal>
  )
}
