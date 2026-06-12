import { getRequestConfig } from 'next-intl/server'

import { routing } from './routing'

// Loads the message catalog for the active locale on the server. Falls back to
// the default locale for any unknown/invalid segment.
export default getRequestConfig(async ({ requestLocale }) => {
  const requested = await requestLocale
  const locale = routing.locales.includes(requested as never)
    ? (requested as string)
    : routing.defaultLocale

  return {
    locale,
    messages: (await import(`../../messages/${locale}.json`)).default,
  }
})
