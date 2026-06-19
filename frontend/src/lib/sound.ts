'use client'

/**
 * Lightweight game sound effects — fully synthesized via the Web Audio API, so there
 * are no audio asset files to ship. Each effect is a few short oscillator/noise
 * blips. Muting is persisted to localStorage; playback "arms" on the first user
 * gesture (browser autoplay policy) and on the mute toggle.
 */
export type SoundName = 'dice' | 'coinGain' | 'coinLoss' | 'build' | 'turn' | 'win'

const STORAGE_KEY = 'mk-sound-muted'

let ctx: AudioContext | null = null
let muted = false

const hasWindow = () => typeof window !== 'undefined'

function getCtx(): AudioContext | null {
  if (!hasWindow()) return null
  if (!ctx) {
    const AC =
      window.AudioContext ||
      (window as unknown as { webkitAudioContext?: typeof AudioContext }).webkitAudioContext
    if (!AC) return null
    try {
      ctx = new AC()
    } catch {
      return null
    }
  }
  if (ctx.state === 'suspended') void ctx.resume()
  return ctx
}

export function isMuted(): boolean {
  if (!hasWindow()) return false
  return window.localStorage.getItem(STORAGE_KEY) === '1'
}

export function setMuted(m: boolean): void {
  muted = m
  if (hasWindow()) window.localStorage.setItem(STORAGE_KEY, m ? '1' : '0')
}

/** Create/resume the audio context — call from within a user gesture to unlock. */
export function unlockAudio(): void {
  getCtx()
}

// ── synthesis helpers ────────────────────────────────────────────────────────
function tone(
  c: AudioContext,
  freq: number,
  t0: number,
  dur: number,
  type: OscillatorType,
  peak = 0.2,
) {
  const osc = c.createOscillator()
  const g = c.createGain()
  osc.type = type
  osc.frequency.setValueAtTime(freq, t0)
  g.gain.setValueAtTime(0.0001, t0)
  g.gain.linearRampToValueAtTime(peak, t0 + 0.01)
  g.gain.exponentialRampToValueAtTime(0.0001, t0 + dur)
  osc.connect(g).connect(c.destination)
  osc.start(t0)
  osc.stop(t0 + dur + 0.02)
}

function noiseBurst(c: AudioContext, t0: number, dur: number, peak = 0.15, freq = 1200) {
  const n = Math.max(1, Math.floor(c.sampleRate * dur))
  const buf = c.createBuffer(1, n, c.sampleRate)
  const data = buf.getChannelData(0)
  for (let i = 0; i < n; i++) data[i] = (Math.random() * 2 - 1) * (1 - i / n) // decaying noise
  const src = c.createBufferSource()
  src.buffer = buf
  const filt = c.createBiquadFilter()
  filt.type = 'bandpass'
  filt.frequency.value = freq
  const g = c.createGain()
  g.gain.setValueAtTime(peak, t0)
  src.connect(filt).connect(g).connect(c.destination)
  src.start(t0)
  src.stop(t0 + dur)
}

const SOUNDS: Record<SoundName, (c: AudioContext, t: number) => void> = {
  // Dice: two quick filtered-noise rattles.
  dice: (c, t) => {
    noiseBurst(c, t, 0.16, 0.18, 1400)
    noiseBurst(c, t + 0.09, 0.12, 0.12, 1000)
  },
  // Coin gain: bright ascending two-note ding.
  coinGain: (c, t) => {
    tone(c, 880, t, 0.12, 'triangle', 0.18)
    tone(c, 1320, t + 0.08, 0.16, 'triangle', 0.18)
  },
  // Coin loss: low descending blip.
  coinLoss: (c, t) => {
    tone(c, 320, t, 0.16, 'sine', 0.18)
    tone(c, 200, t + 0.09, 0.2, 'sine', 0.16)
  },
  // Buy / build: soft low thunk with a tiny click.
  build: (c, t) => {
    tone(c, 180, t, 0.16, 'sine', 0.25)
    noiseBurst(c, t, 0.04, 0.08, 600)
  },
  // Your turn: gentle two-note chime.
  turn: (c, t) => {
    tone(c, 660, t, 0.16, 'triangle', 0.16)
    tone(c, 990, t + 0.1, 0.2, 'triangle', 0.16)
  },
  // Victory: rising three-note jingle.
  win: (c, t) => {
    tone(c, 523, t, 0.18, 'triangle', 0.2)
    tone(c, 659, t + 0.14, 0.18, 'triangle', 0.2)
    tone(c, 784, t + 0.28, 0.32, 'triangle', 0.22)
  },
}

export function playSound(name: SoundName): void {
  if (muted) return
  const c = getCtx()
  if (!c) return
  try {
    SOUNDS[name](c, c.currentTime)
  } catch {
    /* audio is best-effort; never break the game over a sound */
  }
}

// One-time: sync the mute flag and install a gesture-based unlock (client only).
if (hasWindow()) {
  muted = isMuted()
  const unlock = () => {
    getCtx()
    window.removeEventListener('pointerdown', unlock)
    window.removeEventListener('keydown', unlock)
    window.removeEventListener('touchstart', unlock)
  }
  window.addEventListener('pointerdown', unlock)
  window.addEventListener('keydown', unlock)
  window.addEventListener('touchstart', unlock)
}
