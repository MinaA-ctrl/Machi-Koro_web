'use client'

import { useTranslations } from 'next-intl'

/**
 * Localized card/landmark name lookup. The engine tags cards/landmarks by id; the
 * `cards` catalog holds the EN/RU display names (landmarks share the namespace
 * since they share ids). Falls back to a provided English name (the engine's
 * `card_defs[id].name`) or the raw id for any id missing from the catalog.
 */
export function useCardName() {
  const t = useTranslations('cards')
  return (id: string, fallback?: string): string =>
    t.has(id) ? t(id) : (fallback ?? id)
}
