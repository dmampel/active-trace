import { render, screen } from '@testing-library/react'
import { MemoryRouter, Routes, Route } from 'react-router-dom'
import { AuthContext } from '@/features/auth/context/AuthContext'
import { AuthGuard } from './AuthGuard'
import type { AuthContextValue } from '@/shared/types/auth'

const mockUser = {
  id: '1',
  email: 'test@example.com',
  nombre: 'Test',
  apellido: 'User',
  roles: ['PROFESOR'],
  permissions: ['comisiones:read'],
}

function makeContextValue(overrides: Partial<AuthContextValue> = {}): AuthContextValue {
  return {
    user: null,
    session: null,
    isAuthenticated: false,
    hasPermission: () => false,
    setSession: () => undefined,
    clearSession: () => undefined,
    ...overrides,
  }
}

function TestTree({
  contextValue,
  requiredPermission,
}: {
  contextValue: AuthContextValue
  requiredPermission?: string
}) {
  return (
    <MemoryRouter initialEntries={['/protected']}>
      <AuthContext.Provider value={contextValue}>
        <Routes>
          <Route path="/login" element={<div>Login Page</div>} />
          <Route
            path="/protected"
            element={
              <AuthGuard requiredPermission={requiredPermission}>
                <div>Protected Content</div>
              </AuthGuard>
            }
          />
        </Routes>
      </AuthContext.Provider>
    </MemoryRouter>
  )
}

describe('AuthGuard', () => {
  it('redirects to /login when not authenticated', () => {
    render(<TestTree contextValue={makeContextValue({ isAuthenticated: false })} />)
    expect(screen.getByText('Login Page')).toBeInTheDocument()
    expect(screen.queryByText('Protected Content')).not.toBeInTheDocument()
  })

  it('renders Forbidden when authenticated but missing required permission', () => {
    const ctx = makeContextValue({
      isAuthenticated: true,
      user: mockUser,
      hasPermission: () => false,
    })
    render(<TestTree contextValue={ctx} requiredPermission="liquidaciones:read" />)
    expect(screen.getByText(/acceso denegado/i)).toBeInTheDocument()
    expect(screen.queryByText('Protected Content')).not.toBeInTheDocument()
  })

  it('renders children when authenticated and permission matches', () => {
    const ctx = makeContextValue({
      isAuthenticated: true,
      user: mockUser,
      hasPermission: (perm) => perm === 'comisiones:read',
    })
    render(<TestTree contextValue={ctx} requiredPermission="comisiones:read" />)
    expect(screen.getByText('Protected Content')).toBeInTheDocument()
  })

  it('renders children when authenticated with no requiredPermission specified', () => {
    const ctx = makeContextValue({ isAuthenticated: true, user: mockUser })
    render(<TestTree contextValue={ctx} />)
    expect(screen.getByText('Protected Content')).toBeInTheDocument()
  })
})
