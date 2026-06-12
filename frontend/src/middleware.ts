import createMiddleware from 'next-intl/middleware'

import { routing } from './i18n/routing'

// Adds the locale prefix, negotiates from Accept-Language, and redirects `/`.
export default createMiddleware(routing)

export const config = {
  // Match everything except Next internals, API routes, and static files.
  matcher: ['/((?!api|_next|_vercel|.*\\..*).*)'],
}
