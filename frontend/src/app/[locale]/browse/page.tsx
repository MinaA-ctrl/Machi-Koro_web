import { setRequestLocale } from 'next-intl/server'

import { AppHeader } from '@/components/AppHeader'
import { BrowseTables } from '@/components/lobby/BrowseTables'

export default async function BrowsePage({
  params,
}: {
  params: Promise<{ locale: string }>
}) {
  const { locale } = await params
  setRequestLocale(locale)
  return (
    <div className="flex min-h-screen flex-col">
      <AppHeader />
      <main className="mx-auto w-full max-w-3xl flex-1 px-container-padding py-6">
        <BrowseTables />
      </main>
    </div>
  )
}
