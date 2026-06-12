'use client'

import { useTranslations } from 'next-intl'
import { useState } from 'react'
import type { ReactNode } from 'react'

import {
  Button,
  CoinChip,
  DiceNumberBadge,
  FamilyBand,
  Modal,
  PaperCard,
  useToast,
} from '@/components/ui'
import type { FamilyKey } from '@/lib/families'

/**
 * S3.1 styleguide route — renders every base atom straight from the tokens, and
 * proves the locale toggle flips a live string (the sample sentence + button
 * labels re-render EN↔RU via the AppHeader switcher).
 */
export function Styleguide() {
  const t = useTranslations('styleguide')
  const { show } = useToast()
  const [modalOpen, setModalOpen] = useState(false)

  const families: FamilyKey[] = ['blue', 'green', 'red', 'purple', 'gold']

  return (
    <div className="space-y-section-margin pb-16">
      <header>
        <h1 className="font-display text-display-lg text-on-surface">{t('title')}</h1>
        <p className="mt-1 font-body text-body-lg text-on-surface-variant">{t('subtitle')}</p>
        <p className="mt-3 font-body text-body-md italic text-on-surface-variant">
          “{t('sampleString')}”
        </p>
      </header>

      <Section title={t('buttons')}>
        <div className="flex flex-wrap items-center gap-3">
          <Button variant="primary">Primary</Button>
          <Button variant="secondary">Secondary</Button>
          <Button variant="ghost">Ghost</Button>
          <Button variant="danger">Danger</Button>
          <Button variant="primary" size="sm">
            Small
          </Button>
          <Button variant="primary" size="lg">
            Large
          </Button>
          <Button variant="primary" disabled>
            Disabled
          </Button>
        </div>
      </Section>

      <Section title={t('cards')}>
        <div className="flex flex-wrap gap-card-gap">
          {(['flat', 'card', 'float'] as const).map((el) => (
            <PaperCard key={el} elevation={el} className="w-40 p-4">
              <p className="font-label text-sm">{el}</p>
              <p className="font-body text-xs text-on-surface-variant">paper · grain · edge</p>
            </PaperCard>
          ))}
        </div>
      </Section>

      <Section title={t('coins')}>
        <div className="flex items-center gap-4">
          <CoinChip value={3} size="sm" />
          <CoinChip value={24} size="md" />
          <CoinChip value={99} size="lg" />
          <CoinChip value={5} size="md" signed />
        </div>
      </Section>

      <Section title={t('families')}>
        <div className="flex flex-wrap gap-card-gap">
          {families.map((family) => (
            <PaperCard key={family} className="w-32 overflow-hidden">
              <FamilyBand family={family}>
                <span className="capitalize">{family}</span>
                <DiceNumberBadge value={1} />
              </FamilyBand>
              <div className="p-3">
                <p className="font-body text-xs text-on-surface-variant">Establishment</p>
                <div className="mt-2 flex items-center justify-between">
                  <span aria-hidden className="text-xl">
                    🏠
                  </span>
                  <CoinChip value={2} size="sm" />
                </div>
              </div>
            </PaperCard>
          ))}
        </div>
      </Section>

      <Section title={t('dice')}>
        <div className="flex items-center gap-3">
          <DiceNumberBadge value={1} />
          <DiceNumberBadge value={6} />
          <DiceNumberBadge value={[2, 3]} />
          <DiceNumberBadge value={[12, 14]} />
          <DiceNumberBadge value={9} active={false} />
        </div>
      </Section>

      <Section title={t('modals')}>
        <div className="flex flex-wrap gap-3">
          <Button onClick={() => setModalOpen(true)}>{t('openModal')}</Button>
          <Button variant="secondary" onClick={() => show(t('fireToast'), 'success')}>
            {t('fireToast')}
          </Button>
        </div>
        <Modal
          open={modalOpen}
          onClose={() => setModalOpen(false)}
          title={t('openModal')}
          actions={
            <>
              <Button variant="ghost" onClick={() => setModalOpen(false)}>
                Cancel
              </Button>
              <Button onClick={() => setModalOpen(false)}>Confirm</Button>
            </>
          }
        >
          <p>{t('sampleString')}</p>
        </Modal>
      </Section>
    </div>
  )
}

function Section({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section>
      <h2 className="mb-3 font-heading text-headline-md text-on-surface">{title}</h2>
      {children}
    </section>
  )
}
