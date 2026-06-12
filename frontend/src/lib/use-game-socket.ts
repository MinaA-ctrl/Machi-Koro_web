'use client'

import { useEffect, useRef, useState } from 'react'

import { useToast } from '@/components/ui'
import { useGameStore } from '@/store/game-store'
import type { GamePrompt, GameWsEvent } from '@/types/game'
import { connectSocket } from './ws'
import type { Socket } from './ws'

/**
 * Game channel (`/ws/{code}/game/{seat}?token=…`). Authenticates with the per-seat
 * WS token; on 4401 (bad token) it does NOT reconnect. Routes server frames:
 *   state_update → store (the authoritative snapshot the whole board renders from)
 *   game_toast   → toast
 *   coin_event   → coin pulse (this client's seat)
 *   prompt       → ignored here; the structured prompt is already in state.pending_prompt
 *
 * Returns `send` for action senders and a `status` for the connection banner.
 */
export function useGameSocket(
  code: string,
  seat: number,
  token: string,
): { send: (data: unknown) => void; status: 'connecting' | 'open' | 'closed' } {
  const { show } = useToast()
  const setState = useGameStore((s) => s.setState)
  const setConnectedCount = useGameStore((s) => s.setConnectedCount)
  const setPrompt = useGameStore((s) => s.setPrompt)
  const pulseCoins = useGameStore((s) => s.pulseCoins)
  const socketRef = useRef<Socket | null>(null)
  const [status, setStatus] = useState<'connecting' | 'open' | 'closed'>('connecting')

  useEffect(() => {
    const socket = connectSocket<GameWsEvent>({
      path: `/ws/${code}/game/${seat}?token=${encodeURIComponent(token)}`,
      onOpen: () => setStatus('open'),
      onClose: (closeCode) => setStatus(closeCode === 4401 ? 'closed' : 'connecting'),
      onEvent: (event) => {
        switch (event.event) {
          case 'state_update':
            setState(event.state)
            setConnectedCount(event.connected_count)
            break
          case 'game_toast':
            show(event.text, 'info')
            break
          case 'game_prompt':
            // The structured interactive prompt for the active player. The store
            // clears it when the next snapshot reports pending_prompt === null.
            setPrompt(event as unknown as GamePrompt)
            break
          case 'game_events':
            // Granular keyed-event stream (dice/payout/market-reveal). The board
            // animates reveals by diffing state; this channel is reserved for the
            // S3.5 translatable log. No-op for now.
            break
          case 'coin_event':
            // changes belong to this client's seat (server filters per-socket).
            pulseCoins([seat])
            break
          case 'player_left_game':
            show(`${event.name} left`, 'warning')
            break
          case 'player_rejoined_game':
            show(`${event.name} rejoined`, 'success')
            break
          default:
            break
        }
      },
    })
    socketRef.current = socket
    return () => {
      socket.close()
      socketRef.current = null
    }
  }, [code, seat, token, setState, setConnectedCount, setPrompt, pulseCoins, show])

  return {
    send: (data: unknown) => socketRef.current?.send(data),
    status,
  }
}
