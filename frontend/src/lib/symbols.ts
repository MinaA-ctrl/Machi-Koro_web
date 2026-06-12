import type { CardSymbol } from '@/types/game'

/**
 * Card-symbol → glyph. Stand-in emoji for the thick rounded-stroke icons the
 * design calls for; swap for an SVG icon set without touching callers. Mirrors the
 * `symbol` field on the engine's CARD_DEFS.
 */
const SYMBOL_GLYPH: Record<CardSymbol, string> = {
  wheat: '🌾',
  cow: '🐄',
  gear: '⚙️',
  bread: '🍞',
  cup: '☕',
  factory: '🏭',
  fruit: '🍎',
  fish: '🐟',
  tower: '🗼',
  grape: '🍇',
  grain: '🌽',
  store: '🏪',
  restaurant: '🍽️',
  loan: '💵',
}

export function symbolGlyph(symbol: string | undefined): string {
  return (symbol && SYMBOL_GLYPH[symbol as CardSymbol]) || '🏠'
}

/** Collapse an engine `dice` list into a single number or a [min,max] range. */
export function diceLabel(dice: number[]): number | [number, number] {
  if (dice.length === 0) return 0
  const min = Math.min(...dice)
  const max = Math.max(...dice)
  return min === max ? min : [min, max]
}
