import { defineRouting } from 'next-intl/routing'

// EN + RU per the Stage-3 plan (D4). Default locale comes from the account
// `language` at sign-in; the URL prefix is the source of truth thereafter.
export const routing = defineRouting({
  locales: ['en', 'ru'],
  defaultLocale: 'en',
  // Keep the locale prefix always-on so /ru/... and /en/... are explicit and
  // shareable; the home redirect handles the bare `/`.
  localePrefix: 'always',
})

export type Locale = (typeof routing.locales)[number]
