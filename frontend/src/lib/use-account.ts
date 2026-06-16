'use client'

import { useQuery } from '@tanstack/react-query'

import { api } from './api'
import type { UserOut } from '@/types/api'

/**
 * The current account from `/auth/me`. Returns the guest or registered user; errors
 * (no token) leave `data` undefined. Header/account UI keys off `data?.kind` to tell
 * a registered sign-in from a guest. Invalidate ['me'] after login/register/logout.
 */
export function useAccount() {
  return useQuery<UserOut>({
    queryKey: ['me'],
    queryFn: () => api.me(),
    retry: false,
    staleTime: 60_000,
  })
}
