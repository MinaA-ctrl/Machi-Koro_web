import { setRequestLocale } from 'next-intl/server'

import { BoardPreview } from '@/components/board/BoardPreview'

/**
 * Dev-only visual harness — renders the board layout from a canned Basic state
 * (no backend/socket). `?prompt=<type>` overlays a Sharp/interactive prompt fixture;
 * `?vs=1` shows the 10-card Variable-Supply market. The live board is `/game/[code]`.
 */
export default async function BoardPreviewPage({
  params,
  searchParams,
}: {
  params: Promise<{ locale: string }>
  searchParams: Promise<{ prompt?: string; vs?: string }>
}) {
  const { locale } = await params
  const { prompt, vs } = await searchParams
  setRequestLocale(locale)
  return <BoardPreview promptKey={prompt} vs={vs === '1'} />
}
