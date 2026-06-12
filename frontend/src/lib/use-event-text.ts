'use client'

import { useTranslations } from 'next-intl'

import type { KeyedEvent } from '@/types/game'
import { useCardName } from './i18n-names'

/**
 * Renders a keyed game event (`state.events[i]`) to a localized log line. Switches
 * on `event.t` and reads its params; card/landmark ids are resolved to localized
 * names via the `cards` catalog. Player names in events are already display strings.
 * An unknown type degrades to its raw key rather than throwing — forward-compatible
 * if the engine adds an event before the catalog catches up.
 */
export function useEventText() {
  const t = useTranslations('log')
  const cardName = useCardName()

  return (e: KeyedEvent): string => {
    const s = (k: string): string => String(e[k] ?? '')
    const n = (k: string): number => Number(e[k] ?? 0)
    const card = (k: string): string => cardName(s(k))
    const list = (k: string): string[] => (Array.isArray(e[k]) ? (e[k] as string[]) : [])

    switch (e.t) {
      case 'roll':
        return t('roll', { name: s('name'), total: n('total') })
      case 'reroll':
        return t('reroll', { name: s('name'), total: n('total') })
      case 'income':
        return t('income', { name: s('name'), amount: n('amount'), source: card('source') })
      case 'take':
        return t('take', {
          taker: s('taker_name'),
          payer: s('payer_name'),
          amount: n('amount'),
          source: card('source'),
        })
      case 'bank_pay':
        return t('bank_pay', { name: s('name'), amount: n('amount'), source: card('source') })
      case 'park_split':
        return t('park_split', { name: s('name') })
      case 'city_hall':
        return t('city_hall', { name: s('name') })
      case 'tuna_payout': {
        const dice = list('dice')
        return t('tuna_payout', {
          name: s('name'),
          amount: n('amount'),
          d0: dice[0] ?? '',
          d1: dice[1] ?? '',
          total: n('total'),
        })
      }
      case 'renovation_reopen':
        return t('renovation_reopen', { name: s('name'), card: card('card_id') })
      case 'renovation_close':
        return t('renovation_close', { name: s('name'), card: card('card_id') })
      case 'cleaning':
        return t('cleaning', { name: s('name'), count: n('count'), card: card('card_id') })
      case 'tech_invest':
        return t('tech_invest', { name: s('name'), total: n('total') })
      case 'demolish':
        return t('demolish', { name: s('name'), landmark: card('landmark_id') })
      case 'moving_give':
        return t('moving_give', { name: s('name'), card: card('card_id'), target: s('target_name') })
      case 'trade':
        return t('trade', {
          name: s('name'),
          card: card('card_id'),
          opp: s('opp_name'),
          oppCard: card('opp_card_id'),
        })
      case 'tuna_announce':
        return t('tuna_announce', { names: list('names').join(', ') })
      case 'buy_card':
        return t('buy_card', { name: s('name'), card: card('card_id') })
      case 'buy_landmark':
        return t('buy_landmark', { name: s('name'), landmark: card('landmark_id') })
      case 'loan_build':
        return t('loan_build', { name: s('name') })
      case 'amusement_park':
        return t('amusement_park', { name: s('name') })
      case 'win':
        return t('win', { name: s('name') })
      case 'win_forfeit':
        return t('win_forfeit', { name: s('name') })
      case 'no_income':
        return t('no_income')
      case 'bc_offer':
        return t('bc_offer', { name: s('name') })
      case 'trade_done':
        return t('trade_done', {
          name: s('name'),
          card: card('card_id'),
          opp: s('opp_name'),
          oppCard: card('opp_card_id'),
        })
      case 'skip_build':
        return t('skip_build', { name: s('name') })
      case 'market_reveal': {
        const revealed = list('revealed')
        return revealed.length > 0
          ? t('market_reveal', { card: card('bought_card_id'), revealed: revealed.map((id) => cardName(id)).join(', ') })
          : t('market_reveal_empty', { card: card('bought_card_id') })
      }
      default:
        return t('unknown', { type: e.t })
    }
  }
}
