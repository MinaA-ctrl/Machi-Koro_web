'use client'

import { useTranslations } from 'next-intl'
import { useEffect, useMemo } from 'react'

import { useRouter } from '@/i18n/navigation'
import { actions } from '@/lib/game-actions'
import { getMembership } from '@/lib/membership'
import { useGameSocket } from '@/lib/use-game-socket'
import { useGameStore } from '@/store/game-store'
import { PaperCard } from '@/components/ui'

import { BoardView } from './BoardView'

/**
 * Board orchestrator. Connects the game WebSocket using the per-seat token from
 * table membership, mirrors every `state_update` into the store, and renders the
 * whole board as a pure view over that snapshot. All actions round-trip through the
 * server — nothing about the outcome is decided here.
 */
export function GameBoard({ code }: { code: string }) {
  const router = useRouter()
  const membership = useMemo(() => getMembership(code), [code])

  const setMySeat = useGameStore((s) => s.setMySeat)
  const reset = useGameStore((s) => s.reset)

  // No seat token → the player never joined/started this table here. Send them to
  // the waiting room to (re)join.
  useEffect(() => {
    if (!membership) router.push(`/table/${code}`)
  }, [membership, code, router])

  useEffect(() => {
    setMySeat(membership?.seat ?? null)
    return () => reset()
  }, [membership?.seat, setMySeat, reset])

  if (!membership) return null
  return <ConnectedBoard code={code} seat={membership.seat} token={membership.wsToken} />
}

function ConnectedBoard({ code, seat, token }: { code: string; seat: number; token: string }) {
  const t = useTranslations('board')
  const router = useRouter()
  const { send, status } = useGameSocket(code, seat, token)
  const state = useGameStore((s) => s.state)
  const mySeat = useGameStore((s) => s.mySeat)
  const currentPrompt = useGameStore((s) => s.currentPrompt)

  const handlers = useMemo(
    () => ({
      onRoll: (dc: 1 | 2) => actions.roll(send, dc),
      onEndTurn: () => actions.skipBuild(send),
      onBuyEstablishment: (id: string) => actions.buyEstablishment(send, id),
      onBuildLandmark: (id: string) => actions.buildLandmark(send, id),
      onTechInvest: () => actions.techStartupInvest(send),
      onPromptYesNo: (answer: boolean) => actions.promptYesNo(send, answer),
      onTunaRoll: () => actions.tunaRoll(send),
      onTvStationPick: (s: number) => actions.tvStationPick(send, s),
      onCleaningPick: (cardType: string) => actions.cleaningCompanyPick(send, cardType),
      onDemolitionPick: (id: string) => actions.demolitionPick(send, id),
      onMovingPick: (cardId: string, s: number) => actions.movingCompanyPick(send, cardId, s),
      onBusinessTrade: (myCard: string, oppSeat: number, oppCard: string) =>
        actions.businessCenterTrade(send, myCard, oppSeat, oppCard),
      onBusinessSkip: () => actions.skipBusinessCenter(send),
      onPlayAgain: () => actions.newGame(send),
      onBackToLobby: () => router.push('/'),
    }),
    [send, router],
  )

  if (status === 'closed') return <CenterNotice text={t('authFailed')} />
  if (!state) return <CenterNotice text={t('connecting')} />

  // Only surface a prompt that targets this seat.
  const myPrompt = currentPrompt && currentPrompt.active_seat === seat ? currentPrompt : null

  return <BoardView state={state} seat={seat} mySeat={mySeat} prompt={myPrompt} handlers={handlers} />
}

function CenterNotice({ text }: { text: string }) {
  return (
    <div className="flex min-h-screen items-center justify-center px-container-padding">
      <PaperCard className="p-8 text-center">
        <p className="font-body text-body-lg text-on-surface-variant">{text}</p>
      </PaperCard>
    </div>
  )
}
