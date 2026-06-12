'use client'

/**
 * Minimal reconnecting WebSocket client shared by the lobby and game channels.
 *
 * The Stage-2 backend keeps per-room state in memory and tolerates reconnects
 * (restart-survival on the game channel; presence rebroadcast on the lobby). This
 * client mirrors that: it auto-reconnects with capped backoff, parses JSON frames,
 * and surfaces typed events to a single handler. It does NOT buffer outbound
 * messages across a drop — callers re-derive state from the next snapshot/refetch.
 */
// Resolve the WS base. In prod the app is served same-origin behind nginx, which
// proxies `/api/ws/...` → backend; there `NEXT_PUBLIC_WS_BASE` is a relative path
// like `/api` and we derive the ws(s):// origin from the page. An absolute
// ws://host base (local dev pointing straight at the backend) is used verbatim.
function resolveWsBase(): string {
  const configured = process.env.NEXT_PUBLIC_WS_BASE ?? 'ws://localhost:8000'
  if (configured.startsWith('ws://') || configured.startsWith('wss://')) return configured
  if (typeof window === 'undefined') return configured // SSR: never opens a socket
  const scheme = window.location.protocol === 'https:' ? 'wss' : 'ws'
  const prefix = configured.startsWith('/') ? configured : `/${configured}`
  return `${scheme}://${window.location.host}${prefix === '/' ? '' : prefix}`
}

const WS_BASE = resolveWsBase()

export interface SocketHandlers<E> {
  onEvent: (event: E) => void
  onOpen?: () => void
  onClose?: (code: number) => void
}

export interface Socket {
  send: (data: unknown) => void
  close: () => void
}

interface ConnectOpts<E> extends SocketHandlers<E> {
  /** Path after the WS base, e.g. `/ws/ABCD/lobby/0`. Query string included. */
  path: string
  /** Close codes that must NOT trigger a reconnect (e.g. 4401 bad WS token). */
  fatalCodes?: number[]
}

export function connectSocket<E>(opts: ConnectOpts<E>): Socket {
  const { path, onEvent, onOpen, onClose, fatalCodes = [4401] } = opts
  const url = `${WS_BASE}${path}`

  let ws: WebSocket | null = null
  let closedByCaller = false
  let attempt = 0
  let reconnectTimer: ReturnType<typeof setTimeout> | null = null

  const open = () => {
    ws = new WebSocket(url)

    ws.onopen = () => {
      attempt = 0
      onOpen?.()
    }

    ws.onmessage = (e) => {
      try {
        onEvent(JSON.parse(e.data) as E)
      } catch {
        /* ignore non-JSON frames */
      }
    }

    ws.onclose = (e) => {
      onClose?.(e.code)
      if (closedByCaller || fatalCodes.includes(e.code)) return
      // Capped exponential backoff: 0.5s, 1s, 2s, 4s … max 8s.
      const delay = Math.min(8000, 500 * 2 ** attempt)
      attempt += 1
      reconnectTimer = setTimeout(open, delay)
    }

    ws.onerror = () => {
      // Let onclose drive reconnect; closing here avoids a half-open socket.
      ws?.close()
    }
  }

  open()

  return {
    send: (data: unknown) => {
      if (ws?.readyState === WebSocket.OPEN) {
        ws.send(typeof data === 'string' ? data : JSON.stringify(data))
      }
    },
    close: () => {
      closedByCaller = true
      if (reconnectTimer) clearTimeout(reconnectTimer)
      ws?.close()
    },
  }
}

export { WS_BASE }
