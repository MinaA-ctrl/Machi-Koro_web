'use client'

import { BOARD_FIXTURE, BOARD_FIXTURE_VS, PROMPT_FIXTURES } from '@/lib/board-fixture'
import type { GamePrompt } from '@/types/game'
import { BoardView } from './BoardView'

const noop = () => {}
const NOOP_HANDLERS = {
  onRoll: noop,
  onEndTurn: noop,
  onBuyEstablishment: noop,
  onBuildLandmark: noop,
  onTechInvest: noop,
  onPromptYesNo: noop,
  onTunaRoll: noop,
  onTvStationPick: noop,
  onCleaningPick: noop,
  onDemolitionPick: noop,
  onMovingPick: noop,
  onBusinessTrade: noop,
  onBusinessSkip: noop,
  onPlayAgain: noop,
  onBackToLobby: noop,
}

/**
 * Client wrapper for the dev board preview. `promptKey` selects a canned prompt
 * fixture to render its overlay; `vs` swaps in the Variable-Supply market.
 */
export function BoardPreview({ promptKey, vs }: { promptKey?: string; vs?: boolean }) {
  const prompt: GamePrompt | null = (promptKey && PROMPT_FIXTURES[promptKey]) || null
  const state = vs ? BOARD_FIXTURE_VS : BOARD_FIXTURE
  return <BoardView state={state} seat={0} mySeat={0} prompt={prompt} handlers={NOOP_HANDLERS} />
}
