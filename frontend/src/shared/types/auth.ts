export type PermissionString = string

export interface User {
  id: string
  email: string
  nombre: string
  apellido: string
  roles: string[]
  permissions: PermissionString[]
}

export interface Session {
  access_token: string
  refresh_token: string
  user: User
}

export interface AuthContextValue {
  user: User | null
  session: Session | null
  isAuthenticated: boolean
  hasPermission: (perm: PermissionString) => boolean
  setSession: (session: Session) => void
  clearSession: () => void
}
