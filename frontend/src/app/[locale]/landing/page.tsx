import { setRequestLocale } from 'next-intl/server'

import { AppHeader } from '@/components/AppHeader'
import { LandingPage } from '@/components/landing/LandingPage'

export default async function Landing({
  params,
}: {
  params: Promise<{ locale: string }>
}) {
  const { locale } = await params
  setRequestLocale(locale)
  return (
    <div className="flex min-h-screen flex-col">
      <AppHeader />
      <LandingPage />
    </div>
  )
}
