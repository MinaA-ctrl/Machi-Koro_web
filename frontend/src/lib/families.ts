/**
 * Establishment-family color mapping.
 *
 * The engine tags every card with a `type` string ("Blue Primary",
 * "Green Secondary", "Red Restaurant", "Purple Major"). The four band colors are
 * pinned in tailwind.config.ts (`family.*`). This module is the single place that
 * maps engine type → family key → the Tailwind classes used by cards/bands, so a
 * color change happens in exactly one token and one mapping.
 *
 * a11y: ink color per band is chosen for ≥ AA contrast against that band. The
 * light family tints (blue/green/red/purple at full saturation) all clear 4.5:1
 * against on-surface ink (#1f1b13), so we use dark ink on every band.
 */
export type FamilyKey = 'blue' | 'green' | 'red' | 'purple' | 'gold'

export interface FamilyStyle {
  /** Tailwind bg class for the card header band. */
  band: string
  /** Tailwind text class — AA-legible on the band. */
  ink: string
  /** Pale dot/ring used on opponent mini-cards. */
  dot: string
}

const FAMILY_STYLES: Record<FamilyKey, FamilyStyle> = {
  blue: { band: 'bg-family-blue', ink: 'text-on-surface', dot: 'bg-family-blue' },
  green: { band: 'bg-family-green', ink: 'text-on-surface', dot: 'bg-family-green' },
  red: { band: 'bg-family-red', ink: 'text-on-surface', dot: 'bg-family-red' },
  purple: { band: 'bg-family-purple', ink: 'text-on-surface', dot: 'bg-family-purple' },
  gold: { band: 'bg-family-gold', ink: 'text-on-primary-container', dot: 'bg-family-gold' },
}

/** Map an engine card `type` string to a family key. */
export function familyFromType(type: string | undefined): FamilyKey {
  if (!type) return 'gold'
  const head = type.split(' ')[0]?.toLowerCase()
  switch (head) {
    case 'blue':
      return 'blue'
    case 'green':
      return 'green'
    case 'red':
      return 'red'
    case 'purple':
      return 'purple'
    default:
      return 'gold'
  }
}

export function familyStyle(family: FamilyKey): FamilyStyle {
  return FAMILY_STYLES[family]
}

export function familyStyleFromType(type: string | undefined): FamilyStyle {
  return FAMILY_STYLES[familyFromType(type)]
}
