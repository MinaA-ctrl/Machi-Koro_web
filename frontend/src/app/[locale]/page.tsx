import { setRequestLocale } from 'next-intl/server'

import { AppHeader } from '@/components/AppHeader'
import { HomeLobby } from '@/components/lobby/HomeLobby'
import { LobbyBottomNav } from '@/components/lobby/LobbyBottomNav'

export default async function HomePage({
  params,
}: {
  params: Promise<{ locale: string }>
}) {
  const { locale } = await params
  setRequestLocale(locale)

  return (
    <div className="flex min-h-screen flex-col">
      <AppHeader />
      <main className="mx-auto w-full max-w-5xl flex-1 px-container-padding pb-28 pt-2">
        <HomeLobby />
      </main>
      <LobbyBottomNav />
    </div>
  )
}
