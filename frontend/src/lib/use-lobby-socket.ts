'use client'

import { useEffect, useRef } from 'react'

import { connectSocket } from './ws'
import type { Socket } from './ws'
import type { LobbyWsEvent } from '@/types/game'

interface LobbyCallbacks {
  /** Someone joined or left — re-pull the authoritative roster from REST. */
  onPresenceChange?: () => void
  /** The host left; the table is gone. */
  onTableClosed?: () => void
  /** A seat was kicked (carries the kicked seat). */
  onKicked?: (seat: number) => void
}

/**
 * Lobby presence socket (`/ws/{code}/lobby/{seat}`). The server relays
 * join/left/kicked/closed; we treat REST as the source of truth for the roster and
 * use these events purely as triggers (refetch) and for the two terminal overlays.
 *
 * Returns a `send` ref so the host can broadcast `player_kicked` after the REST
 * kick call, which is how the kicked client learns it was removed (the lobby loop
 * preserves a carried `seat`, per app/ws.py).
 */
export function useLobbySocket(
  code: string | null,
  seat: number | null,
  cb: LobbyCallbacks,
): { send: (data: unknown) => void } {
  const socketRef = useRef<Socket | null>(null)
  // Keep callbacks fresh without reconnecting on every render.
  const cbRef = useRef(cb)
  cbRef.current = cb

  useEffect(() => {
    if (!code || seat == null) return

    const socket = connectSocket<LobbyWsEvent>({
      path: `/ws/${code}/lobby/${seat}`,
      onEvent: (event) => {
        switch (event.event) {
          case 'player_joined':
          case 'player_left':
            cbRef.current.onPresenceChange?.()
            break
          case 'table_closed':
            cbRef.current.onTableClosed?.()
            break
          case 'player_kicked':
            cbRef.current.onKicked?.(Number((event as { seat?: string | number }).seat))
            break
          default:
            // Any other relayed lobby message is also a presence hint.
            cbRef.current.onPresenceChange?.()
        }
      },
    })
    socketRef.current = socket
    return () => {
      socket.close()
      socketRef.current = null
    }
  }, [code, seat])

  return {
    send: (data: unknown) => socketRef.current?.send(data),
  }
}
