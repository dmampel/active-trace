import { type ReactNode } from 'react'
import { Navigate, useLocation } from 'react-router-dom'
import { useAuth } from '@/features/auth/hooks/useAuth'
import { Forbidden } from '@/shared/components/Forbidden'
import type { PermissionString } from '@/shared/types/auth'

interface AuthGuardProps {
  children: ReactNode
  requiredPermission?: PermissionString
}

export function AuthGuard({ children, requiredPermission }: AuthGuardProps) {
  const { isAuthenticated, hasPermission } = useAuth()
  const location = useLocation()

  if (!isAuthenticated) {
    return <Navigate to="/login" state={{ from: location }} replace />
  }

  if (requiredPermission && !hasPermission(requiredPermission)) {
    return <Forbidden />
  }

  return <>{children}</>
}
