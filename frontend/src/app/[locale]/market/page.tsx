import { setRequestLocale } from 'next-intl/server'

import { AppHeader } from '@/components/AppHeader'
import { MarketComingSoon } from '@/components/MarketComingSoon'
import { LobbyBottomNav } from '@/components/lobby/LobbyBottomNav'

export default async function MarketPage({
  params,
}: {
  params: Promise<{ locale: string }>
}) {
  const { locale } = await params
  setRequestLocale(locale)
  return (
    <div className="flex min-h-screen flex-col">
      <AppHeader />
      <main className="mx-auto flex w-full max-w-5xl flex-1 flex-col px-container-padding pb-28 pt-2">
        <MarketComingSoon />
      </main>
      <LobbyBottomNav />
    </div>
  )
}
