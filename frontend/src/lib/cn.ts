/**
 * Tiny class-name joiner — drops falsy values and flattens. Avoids pulling in
 * clsx/tailwind-merge for the atom layer; the design system rarely needs merge
 * conflict resolution because tokens are single-purpose.
 */
export type ClassValue = string | number | false | null | undefined

export function cn(...values: ClassValue[]): string {
  return values.filter(Boolean).join(' ')
}
