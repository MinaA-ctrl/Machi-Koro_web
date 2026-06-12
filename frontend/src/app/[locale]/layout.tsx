import type { Metadata } from 'next'
import { Fredoka, Nunito_Sans } from 'next/font/google'
import { NextIntlClientProvider } from 'next-intl'
import { getMessages, setRequestLocale } from 'next-intl/server'
import { notFound } from 'next/navigation'
import type { ReactNode } from 'react'

import { Providers } from '@/components/Providers'
import { routing } from '@/i18n/routing'

import '@/styles/globals.css'

// Fonts — Fredoka (voice) + Nunito Sans (body), exposed as CSS vars consumed by
// the Tailwind fontFamily tokens.
// NOTE: Fredoka ships no Cyrillic subset; RU headings fall back through the
// fontFamily stack (Nunito Sans → system-ui). Tracked as an S3.5 i18n gap —
// swap to a Cyrillic-capable rounded display face if RU heading fidelity matters.
const fredoka = Fredoka({
  subsets: ['latin', 'latin-ext'],
  weight: ['300', '400', '500', '600', '700'],
  variable: '--font-fredoka',
  display: 'swap',
})

const nunito = Nunito_Sans({
  subsets: ['latin', 'cyrillic'],
  weight: ['300', '400', '600', '700'],
  variable: '--font-nunito',
  display: 'swap',
})

export const metadata: Metadata = {
  title: 'Machi Koro',
  description: 'Build your village — the Cozy Tabletop edition.',
}

// Pre-render both locales at build time.
export function generateStaticParams() {
  return routing.locales.map((locale) => ({ locale }))
}

export default async function LocaleLayout({
  children,
  params,
}: {
  children: ReactNode
  params: Promise<{ locale: string }>
}) {
  const { locale } = await params
  if (!routing.locales.includes(locale as (typeof routing.locales)[number])) notFound()

  // Enables static rendering for this locale.
  setRequestLocale(locale)
  const messages = await getMessages()

  return (
    <html lang={locale} className={`${fredoka.variable} ${nunito.variable}`}>
      <body className="min-h-screen font-body text-on-surface antialiased">
        <NextIntlClientProvider messages={messages}>
          <Providers>{children}</Providers>
        </NextIntlClientProvider>
      </body>
    </html>
  )
}
