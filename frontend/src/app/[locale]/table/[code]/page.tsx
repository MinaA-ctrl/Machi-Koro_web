import { setRequestLocale } from 'next-intl/server'

import { AppHeader } from '@/components/AppHeader'
import { WaitingRoom } from '@/components/lobby/WaitingRoom'

export default async function TablePage({
  params,
}: {
  params: Promise<{ locale: string; code: string }>
}) {
  const { locale, code } = await params
  setRequestLocale(locale)
  return (
    <div className="flex min-h-screen flex-col">
      <AppHeader />
      <main className="mx-auto w-full max-w-2xl flex-1 px-container-padding py-6">
        <WaitingRoom code={code} />
      </main>
    </div>
  )
}
