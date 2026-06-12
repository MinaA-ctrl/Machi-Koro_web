import type { Config } from 'tailwindcss'

/**
 * Tabletop Hearth — the committed token source of truth.
 *
 * Every value here is ported verbatim from DESIGN.md (the Stitch "Cozy Tabletop"
 * spec). This file is the ONLY place raw hex values may live. Anything in the app
 * that needs a color/spacing/radius/shadow references a token from here (or its
 * CSS-var mirror in globals.css) — never an inline hex. A lint rule guards this.
 *
 * The four establishment-family colors are pinned EXACTLY per the Stage-3 task:
 *   blue #5DADE2 · green #7ABF7E · red #E08470 · purple #A98BC4
 * These are the card-band families, distinct from the felt-green `secondary`.
 */
const config: Config = {
  darkMode: 'class',
  content: [
    './src/app/**/*.{ts,tsx}',
    './src/components/**/*.{ts,tsx}',
    './src/**/*.{ts,tsx}',
  ],
  theme: {
    extend: {
      colors: {
        // ── Material-derived surface/role tokens (DESIGN.md `colors`) ──────────
        surface: '#fff8f2',
        'surface-dim': '#e2d9cb',
        'surface-bright': '#fff8f2',
        'surface-container-lowest': '#ffffff',
        'surface-container-low': '#fdf2e4',
        'surface-container': '#f7ecdf',
        'surface-container-high': '#f1e7d9',
        'surface-container-highest': '#ebe1d4',
        'surface-variant': '#ebe1d4',
        'surface-tint': '#795900',
        'on-surface': '#1f1b13',
        'on-surface-variant': '#4f4635',
        'inverse-surface': '#353027',
        'inverse-on-surface': '#faefe2',
        outline: '#817663',
        'outline-variant': '#d2c5af',

        // Primary = Gold (currency, highlights, Buy actions)
        primary: '#795900',
        'on-primary': '#ffffff',
        'primary-container': '#e8b53c',
        'on-primary-container': '#624800',
        'inverse-primary': '#f3bf45',
        'primary-fixed': '#ffdf9f',
        'primary-fixed-dim': '#f3bf45',
        'on-primary-fixed': '#261a00',
        'on-primary-fixed-variant': '#5b4300',

        // Secondary = Felt Green (play-area panels)
        secondary: '#3c6849',
        'on-secondary': '#ffffff',
        'secondary-container': '#bdeec7',
        'on-secondary-container': '#426e4f',
        'secondary-fixed': '#bdeec7',
        'secondary-fixed-dim': '#a2d2ad',
        'on-secondary-fixed': '#00210e',
        'on-secondary-fixed-variant': '#244f33',

        // Tertiary = warm clay
        tertiary: '#755750',
        'on-tertiary': '#ffffff',
        'tertiary-container': '#dab4ab',
        'on-tertiary-container': '#61453f',
        'tertiary-fixed': '#ffdad2',
        'tertiary-fixed-dim': '#e5beb5',
        'on-tertiary-fixed': '#2b1611',
        'on-tertiary-fixed-variant': '#5c403a',

        // Error
        error: '#ba1a1a',
        'on-error': '#ffffff',
        'error-container': '#ffdad6',
        'on-error-container': '#93000a',

        background: '#fff8f2',
        'on-background': '#1f1b13',

        // ── Establishment families — PINNED EXACTLY (task requirement) ─────────
        // `band` = the card header band; `ink` = AA-legible text/icon on that band;
        // `soft` = a pale tint for opponent mini-cards / chips.
        family: {
          blue: '#5DADE2',
          green: '#7ABF7E',
          red: '#E08470',
          purple: '#A98BC4',
          // Landmarks/major are gold-tied; reuse the gold container.
          gold: '#e8b53c',
        },
      },

      borderRadius: {
        // DESIGN.md `rounded`. DEFAULT 8px (inputs), lg 16px (cards/buttons),
        // xl 24px (felt panels), pill = full.
        sm: '0.25rem',
        DEFAULT: '0.5rem',
        md: '0.75rem',
        lg: '1rem',
        xl: '1.5rem',
        full: '9999px',
      },

      spacing: {
        // DESIGN.md `spacing` (8px base rhythm).
        unit: '8px',
        gutter: '16px',
        'card-gap': '12px',
        'container-padding': '24px',
        'section-margin': '40px',
      },

      fontFamily: {
        // Fredoka = the "voice" (headings, numbers, labels); Nunito Sans = body.
        // Loaded via next/font in the root layout, exposed as CSS vars.
        display: ['var(--font-fredoka)', 'Fredoka', 'system-ui', 'sans-serif'],
        heading: ['var(--font-fredoka)', 'Fredoka', 'system-ui', 'sans-serif'],
        label: ['var(--font-fredoka)', 'Fredoka', 'system-ui', 'sans-serif'],
        number: ['var(--font-fredoka)', 'Fredoka', 'system-ui', 'sans-serif'],
        body: ['var(--font-nunito)', '"Nunito Sans"', 'system-ui', 'sans-serif'],
        sans: ['var(--font-nunito)', '"Nunito Sans"', 'system-ui', 'sans-serif'],
      },

      fontSize: {
        // DESIGN.md `typography` scale (size / lineHeight / letterSpacing).
        'display-lg': ['48px', { lineHeight: '1.2', letterSpacing: '-0.02em', fontWeight: '600' }],
        'headline-lg': ['32px', { lineHeight: '1.3', fontWeight: '600' }],
        'headline-lg-mobile': ['24px', { lineHeight: '1.3', fontWeight: '600' }],
        'headline-md': ['24px', { lineHeight: '1.4', fontWeight: '500' }],
        'body-lg': ['18px', { lineHeight: '1.6', fontWeight: '400' }],
        'body-md': ['16px', { lineHeight: '1.6', fontWeight: '400' }],
        'label-lg': ['16px', { lineHeight: '1.2', fontWeight: '500' }],
        'number-xl': ['40px', { lineHeight: '1', fontWeight: '700' }],
      },

      boxShadow: {
        // Ambient Layered Shadows — warm tint rgba(78,52,46,*), never pure black.
        // Level 1 (felt, recessed): inner shadow.
        felt: 'inset 0 2px 6px 0 rgba(78,52,46,0.12)',
        // Level 2 (paper cards/buttons): tight contact + soft float.
        card: '0 2px 2px 0 rgba(78,52,46,0.12), 0 8px 16px -4px rgba(78,52,46,0.15)',
        'card-hover': '0 2px 2px 0 rgba(78,52,46,0.14), 0 12px 24px -6px rgba(78,52,46,0.20)',
        // Token press: shrunk shadow for the 1px-down pressed state.
        'card-press': '0 1px 1px 0 rgba(78,52,46,0.16)',
        // Coin emboss (DESIGN.md Chips → "coin emboss effect"): top highlight +
        // lower inner gold shadow + contact. Shadow tints only, no flat fills.
        'coin-emboss':
          'inset 0 1px 1px rgba(255,255,255,0.55), inset 0 -2px 3px rgba(98,72,0,0.35), 0 1px 2px rgba(78,52,46,0.25)',
        // Level 3 (modals/die): significant height.
        float: '0 8px 16px -4px rgba(78,52,46,0.18), 0 24px 48px -12px rgba(78,52,46,0.24)',
      },

      backdropBlur: {
        modal: '5px',
      },

      keyframes: {
        'toast-in': {
          '0%': { opacity: '0', transform: 'translateY(12px) scale(0.98)' },
          '100%': { opacity: '1', transform: 'translateY(0) scale(1)' },
        },
        'fade-in': {
          '0%': { opacity: '0' },
          '100%': { opacity: '1' },
        },
        'modal-in': {
          '0%': { opacity: '0', transform: 'translateY(8px) scale(0.97)' },
          '100%': { opacity: '1', transform: 'translateY(0) scale(1)' },
        },
        // Dice tumble — used between idle and result; reduced-motion swaps to a snap.
        'dice-tumble': {
          '0%': { transform: 'rotate(0deg) scale(1)' },
          '25%': { transform: 'rotate(180deg) scale(1.08)' },
          '50%': { transform: 'rotate(320deg) scale(0.96)' },
          '75%': { transform: 'rotate(520deg) scale(1.04)' },
          '100%': { transform: 'rotate(720deg) scale(1)' },
        },
        'coin-pop': {
          '0%': { transform: 'translateY(0) scale(0.6)', opacity: '0' },
          '30%': { transform: 'translateY(-10px) scale(1.1)', opacity: '1' },
          '100%': { transform: 'translateY(-28px) scale(1)', opacity: '0' },
        },
        // 10-card Variable Supply: a sold-out slot flips to reveal the drawn card.
        // Reduced-motion neutralizes the transform → it simply fades in.
        'card-reveal': {
          '0%': { opacity: '0', transform: 'rotateY(90deg) scale(0.92)' },
          '60%': { opacity: '1' },
          '100%': { opacity: '1', transform: 'rotateY(0deg) scale(1)' },
        },
      },
      animation: {
        'toast-in': 'toast-in 220ms cubic-bezier(0.22, 1, 0.36, 1)',
        'fade-in': 'fade-in 180ms ease-out',
        'modal-in': 'modal-in 200ms cubic-bezier(0.22, 1, 0.36, 1)',
        'dice-tumble': 'dice-tumble 600ms cubic-bezier(0.34, 1.2, 0.64, 1)',
        'coin-pop': 'coin-pop 900ms ease-out forwards',
        'card-reveal': 'card-reveal 450ms cubic-bezier(0.22, 1, 0.36, 1)',
      },
    },
  },
  plugins: [],
}

export default config
