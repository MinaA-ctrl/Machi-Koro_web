import type { GameState, Player } from '@/types/game'

/**
 * End-game scoring.
 *
 * points = (sum of each opened landmark's price × 2) + leftover coins + place bonus
 * place bonus: 1st +40, 2nd +25, 3rd +10, everyone else +0.
 *
 * "Opened" landmarks are the ones the player actually built — City Hall is pre-built
 * and excluded. Place is the finishing order: the winner first, then by landmarks
 * opened, then by coins.
 */
export interface Standing {
  seat: number
  name: string
  built: number // landmarks opened (excludes City Hall)
  coins: number
  place: number // 1 = winner
  points: number
  isWinner: boolean
}

const PLACE_BONUS: Record<number, number> = { 1: 40, 2: 25, 3: 10 }

function openedLandmarks(p: Player) {
  return p.landmarks.filter((lm) => lm.built && lm.id !== 'city_hall')
}

export function computeStandings(state: GameState): Standing[] {
  const winner = state.winner
  const ranked = [...state.players].sort((a, b) => {
    if ((a.seat === winner) !== (b.seat === winner)) return a.seat === winner ? -1 : 1
    const byBuilt = openedLandmarks(b).length - openedLandmarks(a).length
    if (byBuilt !== 0) return byBuilt
    return b.coins - a.coins
  })

  return ranked.map((p, i) => {
    const place = i + 1
    const opened = openedLandmarks(p)
    const base = opened.reduce((sum, lm) => sum + lm.cost * 2, 0) + p.coins
    return {
      seat: p.seat,
      name: p.name,
      built: opened.length,
      coins: p.coins,
      place,
      points: base + (PLACE_BONUS[place] ?? 0),
      isWinner: p.seat === winner,
    }
  })
}
