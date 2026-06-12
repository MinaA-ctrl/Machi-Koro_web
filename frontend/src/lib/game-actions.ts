/**
 * Typed action senders — the exact message shapes `machi_koro_engine.handle_action`
 * accepts (game_engine.py). Every action is validated server-side against the
 * active seat + phase; these helpers just keep the wire shapes honest.
 */
export type Send = (data: unknown) => void

export const actions = {
  /** Roll. `diceCount` 2 only takes effect if the player owns Train Station. */
  roll: (send: Send, diceCount: 1 | 2 = 1) => send({ event: 'roll', dice_count: diceCount }),

  /** Buy an establishment from the market. */
  buyEstablishment: (send: Send, id: string) =>
    send({ event: 'build', type: 'establishment', id }),

  /** Build a landmark. */
  buildLandmark: (send: Send, id: string) => send({ event: 'build', type: 'landmark', id }),

  /** End the build phase without buying (ends the turn). */
  skipBuild: (send: Send) => send({ event: 'skip_build' }),

  // ── prompt responses (yes/no + tuna) ──────────────────────────────────────
  promptYesNo: (send: Send, answer: boolean) => send({ event: 'prompt_response', answer }),
  tunaRoll: (send: Send) => send({ event: 'tuna_roll' }),

  // ── interactive prompt picks (S3.4) ───────────────────────────────────────
  /** TV Station: take 5 coins from one opponent. */
  tvStationPick: (send: Send, targetSeat: number) =>
    send({ event: 'tv_station_pick', target_seat: targetSeat }),

  /** Cleaning Company (Sharp): close every copy of one establishment type. */
  cleaningCompanyPick: (send: Send, cardType: string) =>
    send({ event: 'cleaning_company_pick', card_type: cardType }),

  /** Demolition Company (Sharp): demolish one of your landmarks for coins. */
  demolitionPick: (send: Send, landmarkId: string) =>
    send({ event: 'demolition_pick', landmark_id: landmarkId }),

  /** Moving Company (Sharp): give one establishment to another player. */
  movingCompanyPick: (send: Send, cardId: string, targetSeat: number) =>
    send({ event: 'moving_company_pick', card_id: cardId, target_seat: targetSeat }),

  /** Business Center: trade one of your cards for an opponent's. */
  businessCenterTrade: (send: Send, myCard: string, oppSeat: number, oppCard: string) =>
    send({ event: 'business_center', my_card: myCard, opp_seat: oppSeat, opp_card: oppCard }),

  /** Business Center: decline the trade. */
  skipBusinessCenter: (send: Send) => send({ event: 'skip_business_center' }),

  /** Tech Startup (Sharp): invest 1 coin onto the card (build phase, once/turn). */
  techStartupInvest: (send: Send) => send({ event: 'tech_startup_invest' }),

  /** New game / rematch at the same table once finished. */
  newGame: (send: Send) => send({ event: 'new_game' }),

  reaction: (send: Send, emoji: string) => send({ event: 'reaction', emoji }),
}
