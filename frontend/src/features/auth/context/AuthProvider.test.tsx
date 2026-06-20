import { render, screen, act } from '@testing-library/react'
import { AuthProvider } from './AuthProvider'
import { useAuth } from '@/features/auth/hooks/useAuth'
import type { Session } from '@/shared/types/auth'

const mockSession: Session = {
  access_token: 'test-access',
  refresh_token: 'test-refresh',
  user: {
    id: '1',
    email: 'test@example.com',
    nombre: 'Test',
    apellido: 'User',
    roles: ['PROFESOR'],
    permissions: ['comisiones:read', 'alumnos:read'],
  },
}

function TestConsumer() {
  const { hasPermission, setSession, isAuthenticated } = useAuth()
  return (
    <div>
      <span data-testid="authenticated">{String(isAuthenticated)}</span>
      <span data-testid="has-perm">{String(hasPermission('comisiones:read'))}</span>
      <span data-testid="no-perm">{String(hasPermission('liquidaciones:read'))}</span>
      <button onClick={() => setSession(mockSession)}>set session</button>
    </div>
  )
}

describe('AuthProvider – hasPermission', () => {
  beforeEach(() => {
    localStorage.clear()
  })

  it('returns false for any permission when no session is active', () => {
    render(
      <AuthProvider>
        <TestConsumer />
      </AuthProvider>,
    )
    expect(screen.getByTestId('authenticated').textContent).toBe('false')
    expect(screen.getByTestId('has-perm').textContent).toBe('false')
  })

  it('returns true for a permission in session and false for one not in session', async () => {
    render(
      <AuthProvider>
        <TestConsumer />
      </AuthProvider>,
    )

    await act(async () => {
      screen.getByRole('button', { name: 'set session' }).click()
    })

    expect(screen.getByTestId('authenticated').textContent).toBe('true')
    expect(screen.getByTestId('has-perm').textContent).toBe('true')
    expect(screen.getByTestId('no-perm').textContent).toBe('false')
  })
})
