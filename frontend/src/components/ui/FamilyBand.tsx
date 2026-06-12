import type { ReactNode } from 'react'

import { cn } from '@/lib/cn'
import { familyStyle, familyStyleFromType } from '@/lib/families'
import type { FamilyKey } from '@/lib/families'

interface FamilyBandProps {
  /** Provide either an explicit family key… */
  family?: FamilyKey
  /** …or the engine card `type` string, which is mapped to a family. */
  type?: string
  children?: ReactNode
  className?: string
}

/**
 * The colored header band at the top of an establishment card (DESIGN.md Cards →
 * Header). Color comes from the pinned `family.*` tokens; ink is chosen for AA
 * contrast on that band by `families.ts`.
 */
export function FamilyBand({ family, type, children, className }: FamilyBandProps) {
  const style = family ? familyStyle(family) : familyStyleFromType(type)
  return (
    <div
      className={cn(
        'flex items-center justify-between rounded-t-lg px-2 py-1 font-label text-sm font-medium',
        style.band,
        style.ink,
        className,
      )}
    >
      {children}
    </div>
  )
}
