import { setRequestLocale } from 'next-intl/server'

import { GameBoard } from '@/components/board/GameBoard'

/**
 * Board route. The create→waiting→start flow lands here once a table is `playing`.
 * Renders the live, server-authoritative board (S3.3). Basic + Harbour play; the
 * Sharp prompts + 10-card Variable-Supply market are layered in S3.4.
 */
export default async function GamePage({
  params,
}: {
  params: Promise<{ locale: string; code: string }>
}) {
  const { locale, code } = await params
  setRequestLocale(locale)
  return <GameBoard code={code} />
}
