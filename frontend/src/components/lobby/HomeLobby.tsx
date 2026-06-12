'use client'

import { useTranslations } from 'next-intl'
import { useState } from 'react'

import { useRouter } from '@/i18n/navigation'
import { ApiError, api } from '@/lib/api'
import { cn } from '@/lib/cn'
import { setMembership } from '@/lib/membership'
import { useEnsureAuth } from '@/lib/use-ensure-auth'
import type { GameVersion } from '@/types/api'
import { Button, PaperCard, useToast } from '@/components/ui'

import { RuleToggle } from './RuleToggle'

/**
 * The lobby home — "Establish New Table" (game-setup form) + "Join Existing"
 * (by-code) + browse entry. Wired to the FastAPI tables API; a guest session is
 * bootstrapped on mount so actions work without an explicit sign-in.
 */
export function HomeLobby() {
  const t = useTranslations('home')
  const { show } = useToast()
  const router = useRouter()
  useEnsureAuth()

  // ── Create-table form state ───────────────────────────────────────────────
  const [name, setName] = useState('')
  const [accessKey, setAccessKey] = useState('')
  const [version, setVersion] = useState<GameVersion>('basic')
  const [sharp, setSharp] = useState(false)
  const [variableSupply, setVariableSupply] = useState(false)
  const [isPublic, setIsPublic] = useState(true)
  const [creating, setCreating] = useState(false)

  // ── Join-by-code state ────────────────────────────────────────────────────
  const [joinCode, setJoinCode] = useState('')
  const [joining, setJoining] = useState(false)

  async function handleCreate() {
    if (creating) return
    setCreating(true)
    try {
      const resp = await api.createTable({
        name: name.trim() || null,
        is_public: isPublic,
        version,
        sharp,
        variable_supply: variableSupply,
        password: accessKey.trim() || null,
      })
      setMembership({ code: resp.code, seat: resp.seat, wsToken: resp.token, isHost: resp.seat === 0 })
      show(t('createTable'), 'success')
      router.push(`/table/${resp.code}`)
    } catch (err) {
      show(err instanceof ApiError ? err.message : t('createTable'), 'error')
    } finally {
      setCreating(false)
    }
  }

  async function handleJoin() {
    const code = joinCode.trim().toUpperCase()
    if (!code || joining) return
    setJoining(true)
    try {
      // Try an open join first; a 403 means it's password-protected — the waiting
      // room route handles the password modal on entry.
      const resp = await api.joinTable(code, {})
      setMembership({ code, seat: resp.seat, wsToken: resp.token, isHost: resp.seat === 0 })
      router.push(`/table/${code}`)
    } catch (err) {
      if (err instanceof ApiError && err.status === 403) {
        // Protected or needs a password — let the table route prompt for it.
        router.push(`/table/${code}`)
        return
      }
      show(err instanceof ApiError ? err.message : 'Error', 'error')
    } finally {
      setJoining(false)
    }
  }

  return (
    <PaperCard className="grid gap-8 p-6 lg:grid-cols-[1.2fr_1fr] lg:p-8">
      {/* ── Establish New Table ─────────────────────────────────────────── */}
      <section className="lg:pr-8" aria-labelledby="establish-heading">
        <h2
          id="establish-heading"
          className="mb-5 flex items-center gap-2 font-heading text-headline-md text-on-surface"
        >
          <span aria-hidden>⊕</span>
          {t('establishTable')}
        </h2>

        <label className="mb-1 block font-label text-sm text-on-surface-variant" htmlFor="table-name">
          {t('tableName')}
        </label>
        <input
          id="table-name"
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder={t('tableNamePlaceholder')}
          className={INPUT}
        />

        <label
          className="mb-1 mt-4 block font-label text-sm text-on-surface-variant"
          htmlFor="access-key"
        >
          {t('accessKey')}
        </label>
        <div className="relative">
          <input
            id="access-key"
            type="password"
            value={accessKey}
            onChange={(e) => setAccessKey(e.target.value)}
            placeholder={t('accessKeyPlaceholder')}
            className={INPUT}
          />
          <span className="pointer-events-none absolute right-3 top-1/2 -translate-y-1/2 text-on-surface-variant" aria-hidden>
            🔒
          </span>
        </div>

        {/* Game rules */}
        <fieldset className="mt-6">
          <legend className="mb-2 font-label text-sm font-medium uppercase tracking-wide text-on-surface-variant">
            {t('gameRules')}
          </legend>

          {/* Version segmented control */}
          <div
            className="mb-3 inline-flex rounded-lg bg-surface-container p-1 shadow-felt"
            role="radiogroup"
            aria-label={t('gameRules')}
          >
            {(['basic', 'harbour'] as const).map((v) => (
              <button
                key={v}
                type="button"
                role="radio"
                aria-checked={version === v}
                onClick={() => setVersion(v)}
                className={cn(
                  'rounded-DEFAULT px-5 py-2 font-label text-sm font-medium transition-colors',
                  version === v
                    ? 'bg-primary text-on-primary shadow-card'
                    : 'text-on-surface-variant hover:bg-surface-container-high',
                )}
              >
                {v === 'basic' ? t('versionBasic') : t('versionHarbour')}
              </button>
            ))}
          </div>

          <div className="grid gap-3 sm:grid-cols-2">
            <RuleToggle
              checked={sharp}
              onChange={setSharp}
              label={t('sharpLabel')}
              hint={t('sharpHint')}
              glyph="💎"
            />
            <RuleToggle
              checked={variableSupply}
              onChange={setVariableSupply}
              label={t('variableSupplyLabel')}
              hint={t('variableSupplyHint')}
              glyph="🃏"
            />
          </div>
        </fieldset>

        {/* Visibility */}
        <div className="mt-4 flex items-center gap-2 font-label text-sm">
          <span className="text-on-surface-variant">{t('visibility')}:</span>
          {(
            [
              ['public', isPublic],
              ['private', !isPublic],
            ] as const
          ).map(([key, on]) => (
            <button
              key={key}
              type="button"
              aria-pressed={on}
              onClick={() => setIsPublic(key === 'public')}
              className={cn(
                'rounded-full px-3 py-1 transition-colors',
                on
                  ? 'bg-secondary-container text-on-secondary-container'
                  : 'text-on-surface-variant hover:bg-surface-container',
              )}
            >
              {key === 'public' ? t('public') : t('private')}
            </button>
          ))}
        </div>

        <Button
          variant="primary"
          size="lg"
          fullWidth
          className="mt-6"
          disabled={creating}
          onClick={handleCreate}
          leading={<span aria-hidden>▶</span>}
        >
          {creating ? t('creating') : t('createTable')}
        </Button>
      </section>

      {/* ── Join Existing ───────────────────────────────────────────────── */}
      <section
        className="flex flex-col border-t border-outline-variant pt-8 lg:border-l lg:border-t-0 lg:pl-8 lg:pt-0"
        aria-labelledby="join-heading"
      >
        <h2
          id="join-heading"
          className="mb-5 flex items-center gap-2 font-heading text-headline-md text-on-surface"
        >
          <span aria-hidden>🔑</span>
          {t('joinExisting')}
        </h2>

        <div className="flex gap-2">
          <input
            value={joinCode}
            onChange={(e) => setJoinCode(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleJoin()}
            placeholder={t('enterCode')}
            aria-label={t('enterCode')}
            className={cn(INPUT, 'flex-1 uppercase tracking-widest')}
          />
          <Button variant="secondary" disabled={joining} onClick={handleJoin}>
            {t('join')}
          </Button>
        </div>
        <p className="mt-2 font-body text-sm text-on-surface-variant">{t('joinHint')}</p>

        <div className="my-6 flex items-center gap-3" aria-hidden>
          <span className="h-px flex-1 bg-outline-variant" />
          <span className="font-label text-xs uppercase tracking-widest text-on-surface-variant">
            {t('or')}
          </span>
          <span className="h-px flex-1 bg-outline-variant" />
        </div>

        <button
          type="button"
          onClick={() => router.push('/browse')}
          className="group flex items-center justify-between rounded-lg border-2 border-dashed border-outline-variant px-4 py-4 text-left transition-colors hover:border-primary hover:bg-surface-container-low"
        >
          <span>
            <span className="block font-heading text-label-lg font-medium text-on-surface">
              {t('browseTables')}
            </span>
            <span className="block font-body text-sm text-on-surface-variant">
              {t('browseHint')}
            </span>
          </span>
          <span className="text-xl text-on-surface-variant transition-transform group-hover:translate-x-1" aria-hidden>
            →
          </span>
        </button>

        <dl className="mt-auto grid grid-cols-2 gap-3 pt-6">
          <Stat value="14" label={t('activeGames')} />
          <Stat value="52" label={t('playersOnline')} />
        </dl>
      </section>
    </PaperCard>
  )
}

const INPUT =
  'w-full rounded-DEFAULT bg-surface-container-low px-3 py-2.5 font-body text-body-md ' +
  'text-on-surface placeholder:text-on-surface-variant/60 border-2 border-secondary-fixed-dim ' +
  'shadow-felt focus:border-secondary focus:outline-none'

function Stat({ value, label }: { value: string; label: string }) {
  return (
    <div className="rounded-lg bg-surface-container-low p-3 text-center shadow-felt">
      <dd className="font-number text-headline-md font-bold text-primary">{value}</dd>
      <dt className="font-label text-xs text-on-surface-variant">{label}</dt>
    </div>
  )
}
