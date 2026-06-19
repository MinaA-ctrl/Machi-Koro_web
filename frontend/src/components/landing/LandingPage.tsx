'use client'

import { useTranslations } from 'next-intl'

import { useRouter, Link } from '@/i18n/navigation'
import { cn } from '@/lib/cn'
import type { CardDef } from '@/types/game'
import { Button } from '@/components/ui'
import { EstablishmentCard } from '@/components/board/EstablishmentCard'

// Real cards from the game, used as on-brand samples (names + effects localize via
// the same catalogs the live board uses).
const SAMPLE_CARDS: CardDef[] = [
  { id: 'wheat_field', name: 'Wheat Field', dice: [1], type: 'Blue Primary', cost: 1, symbol: 'wheat', effect: 'Get 1 coin from the bank.' },
  { id: 'bakery', name: 'Bakery', dice: [2, 3], type: 'Green Secondary', cost: 1, symbol: 'bread', effect: 'Get 1 coin from the bank.' },
  { id: 'cafe', name: 'Café', dice: [3], type: 'Red Restaurant', cost: 2, symbol: 'cup', effect: 'Take 1 coin from the active player.' },
]

/** A decorative pip die (no game state — pure visual flair). */
function Die({ value }: { value: number }) {
  const PIPS: Record<number, number[]> = {
    1: [4], 2: [0, 8], 3: [0, 4, 8], 4: [0, 2, 6, 8], 5: [0, 2, 4, 6, 8], 6: [0, 2, 3, 5, 6, 8],
  }
  return (
    <div className="grid h-14 w-14 grid-cols-3 grid-rows-3 gap-0.5 rounded-xl bg-surface-container-lowest p-2 shadow-card" aria-hidden>
      {Array.from({ length: 9 }).map((_, i) => (
        <span key={i} className={cn('place-self-center rounded-full', PIPS[value]!.includes(i) ? 'h-2 w-2 bg-on-surface' : '')} />
      ))}
    </div>
  )
}

export function LandingPage() {
  const t = useTranslations('landing')
  const router = useRouter()

  const modes = [
    t('modeBasic'), t('modeHarbour'), t('modeSharp'),
    t('modeVariable'), t('modeBilingual'), t('modeAccounts'),
  ]
  const families = [
    { dot: 'bg-family-blue', title: t('family1Title'), body: t('family1Body') },
    { dot: 'bg-family-red', title: t('family2Title'), body: t('family2Body') },
    { dot: 'bg-family-purple', title: t('family3Title'), body: t('family3Body') },
  ]

  return (
    <main className="flex-1 pb-16">
      {/* ── Hero ─────────────────────────────────────────────────────────── */}
      <section className="mx-auto grid w-full max-w-5xl items-center gap-10 px-container-padding py-10 lg:grid-cols-2 lg:py-16">
        <div>
          <h1 className="font-display text-4xl font-bold leading-tight text-on-surface sm:text-5xl">
            {t('heroTitle')}
          </h1>
          <p className="mt-4 max-w-prose font-body text-body-lg text-on-surface-variant">
            {t('heroSubtitle')}
          </p>
          <div className="mt-7 flex flex-wrap gap-3">
            <Button variant="primary" size="lg" onClick={() => router.push('/')}>
              {t('ctaPlay')}
            </Button>
            <Button variant="secondary" size="lg" onClick={() => router.push('/rules')}>
              {t('ctaRules')}
            </Button>
          </div>
          <ul className="mt-7 flex flex-wrap gap-2">
            {modes.map((m) => (
              <li key={m} className="rounded-full bg-surface-container px-3 py-1 font-label text-xs text-on-surface-variant shadow-card">
                {m}
              </li>
            ))}
          </ul>
        </div>
        <div className="flex items-center justify-center gap-4">
          <div className="rotate-[-4deg]">
            <EstablishmentCard card={SAMPLE_CARDS[1]!} />
          </div>
          <div className="flex flex-col gap-3">
            <Die value={5} />
            <Die value={2} />
          </div>
        </div>
      </section>

      {/* ── Real establishments ──────────────────────────────────────────── */}
      <section className="mx-auto w-full max-w-5xl px-container-padding py-8">
        <h2 className="text-center font-heading text-headline-md text-on-surface">{t('cardsTitle')}</h2>
        <p className="mx-auto mt-2 max-w-2xl text-center font-body text-body-md text-on-surface-variant">
          {t('cardsSubtitle')}
        </p>
        <div className="felt-panel mt-6 flex flex-wrap justify-center gap-4 rounded-xl p-6">
          {SAMPLE_CARDS.map((c) => (
            <EstablishmentCard key={c.id} card={c} />
          ))}
        </div>
      </section>

      {/* ── Two feature boxes ────────────────────────────────────────────── */}
      <section className="mx-auto grid w-full max-w-5xl gap-4 px-container-padding py-8 sm:grid-cols-2">
        <FeatureBox glyph="🛡️" title={t('feature1Title')} body={t('feature1Body')} />
        <FeatureBox glyph="🔊" title={t('feature2Title')} body={t('feature2Body')} />
      </section>

      {/* ── Strategic city building ──────────────────────────────────────── */}
      <section className="mx-auto grid w-full max-w-5xl items-center gap-10 px-container-padding py-10 lg:grid-cols-2">
        <div className="flex items-center justify-center gap-3">
          <div className="h-44 w-28 rotate-[-8deg] rounded-xl bg-family-blue/70 shadow-card" aria-hidden />
          <div className="h-48 w-28 rounded-xl bg-family-purple/70 shadow-card" aria-hidden />
          <div className="h-44 w-28 rotate-[8deg] rounded-xl bg-family-green/70 shadow-card" aria-hidden />
        </div>
        <div>
          <h2 className="font-heading text-headline-md text-on-surface">{t('strategyTitle')}</h2>
          <p className="mt-2 font-body text-body-md text-on-surface-variant">{t('strategyBody')}</p>
          <ul className="mt-5 space-y-4">
            {families.map((f) => (
              <li key={f.title} className="flex gap-3">
                <span className={cn('mt-1.5 h-3 w-3 shrink-0 rounded-full', f.dot)} aria-hidden />
                <div>
                  <p className="font-label text-sm font-semibold text-on-surface">{f.title}</p>
                  <p className="font-body text-sm text-on-surface-variant">{f.body}</p>
                </div>
              </li>
            ))}
          </ul>
        </div>
      </section>

      {/* ── Ready to roll ────────────────────────────────────────────────── */}
      <section className="mx-auto w-full max-w-5xl px-container-padding py-8">
        <div className="felt-panel flex flex-col items-center gap-4 rounded-xl px-6 py-12 text-center">
          <h2 className="font-display text-3xl font-bold text-inverse-on-surface sm:text-4xl">
            {t('ctaTitle')}
          </h2>
          <p className="max-w-xl font-body text-body-md text-inverse-on-surface/85">{t('ctaBody')}</p>
          <Button variant="primary" size="lg" className="mt-2" onClick={() => router.push('/')}>
            {t('ctaButton')}
          </Button>
        </div>
      </section>

      {/* ── Footer ───────────────────────────────────────────────────────── */}
      <footer className="mx-auto w-full max-w-5xl px-container-padding pt-8">
        <div className="flex flex-col gap-4 border-t border-outline-variant pt-6 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <p className="font-heading text-headline-md text-on-surface">{t('footerBrand')}</p>
            <p className="font-body text-sm text-on-surface-variant">{t('footerTagline')}</p>
          </div>
          <nav className="flex gap-5 font-label text-sm text-on-surface-variant">
            <Link href="/rules" className="hover:text-on-surface">{t('footerRules')}</Link>
            <Link href="/browse" className="hover:text-on-surface">{t('footerBrowse')}</Link>
          </nav>
        </div>
        <p className="mt-4 font-body text-xs text-on-surface-variant">{t('footerCopyright')}</p>
      </footer>
    </main>
  )
}

function FeatureBox({ glyph, title, body }: { glyph: string; title: string; body: string }) {
  return (
    <div className="rounded-xl bg-surface-container-low p-5 shadow-card">
      <span className="text-2xl" aria-hidden>{glyph}</span>
      <h3 className="mt-2 font-label text-base font-semibold text-on-surface">{title}</h3>
      <p className="mt-1 font-body text-sm text-on-surface-variant">{body}</p>
    </div>
  )
}
