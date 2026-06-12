'use client'

import { useMemo } from 'react'

import type { GamePrompt, GameState } from '@/types/game'

import { BoardTopBar } from './BoardTopBar'
import { FeltTable } from './FeltTable'
import { Market } from './Market'
import { OpponentsStrip } from './OpponentsStrip'
import { PromptOverlay } from './PromptOverlay'
import { WinnerOverlay } from './WinnerOverlay'
import { YourCity } from './YourCity'

export interface BoardHandlers {
  onRoll: (diceCount: 1 | 2) => void
  onEndTurn: () => void
  onBuyEstablishment: (id: string) => void
  onBuildLandmark: (id: string) => void
  onTechInvest: () => void
  onPromptYesNo: (answer: boolean) => void
  onTunaRoll: () => void
  onTvStationPick: (seat: number) => void
  onCleaningPick: (cardType: string) => void
  onDemolitionPick: (landmarkId: string) => void
  onMovingPick: (cardId: string, targetSeat: number) => void
  onBusinessTrade: (myCard: string, oppSeat: number, oppCard: string) => void
  onBusinessSkip: () => void
  onPlayAgain: () => void
  onBackToLobby: () => void
}

interface BoardViewProps {
  state: GameState
  seat: number
  mySeat: number | null
  /** Structured interactive prompt for this client (or null). */
  prompt: GamePrompt | null
  handlers: BoardHandlers
}

/**
 * Presentational board layout — pure view over a GameState snapshot. Used both by
 * the live `ConnectedBoard` (handlers wired to the socket) and by the fixture
 * `board-preview` route (no-op handlers), so the visual layout has a single source
 * of truth and can't drift between the two.
 */
export function BoardView({ state, seat, mySeat, prompt, handlers }: BoardViewProps) {
  const view = useMemo(() => {
    const me = state.players.find((p) => p.seat === seat)
    const opponents = state.players.filter((p) => p.seat !== seat)
    const isMyTurn = state.active_seat === seat
    const activeName = state.players.find((p) => p.seat === state.active_seat)?.name ?? ''
    return { me, opponents, isMyTurn, activeName }
  }, [state, seat])

  const { me, opponents, isMyTurn, activeName } = view

  return (
    <div className="flex min-h-screen flex-col pb-6">
      <BoardTopBar state={state} me={me} isMyTurn={isMyTurn} activeName={activeName} />
      <OpponentsStrip opponents={opponents} activeSeat={state.active_seat} cardDefs={state.card_defs} />

      <div className="grid flex-1 gap-4 px-container-padding py-2 lg:grid-cols-[minmax(0,1fr)_340px]">
        <div className="flex min-w-0 flex-col gap-4">
          <FeltTable
            state={state}
            me={me}
            isMyTurn={isMyTurn}
            onRoll={handlers.onRoll}
            onEndTurn={handlers.onEndTurn}
            onTechInvest={handlers.onTechInvest}
          />
          <Market state={state} me={me} isMyTurn={isMyTurn} onBuy={handlers.onBuyEstablishment} />
        </div>

        <YourCity state={state} me={me} isMyTurn={isMyTurn} onBuildLandmark={handlers.onBuildLandmark} />
      </div>

      <PromptOverlay
        prompt={prompt}
        state={state}
        handlers={{
          onYesNo: handlers.onPromptYesNo,
          onTunaRoll: handlers.onTunaRoll,
          onTvStationPick: handlers.onTvStationPick,
          onCleaningPick: handlers.onCleaningPick,
          onDemolitionPick: handlers.onDemolitionPick,
          onMovingPick: handlers.onMovingPick,
          onBusinessTrade: handlers.onBusinessTrade,
          onBusinessSkip: handlers.onBusinessSkip,
        }}
      />
      <WinnerOverlay
        state={state}
        mySeat={mySeat}
        onPlayAgain={handlers.onPlayAgain}
        onBackToLobby={handlers.onBackToLobby}
      />
    </div>
  )
}
