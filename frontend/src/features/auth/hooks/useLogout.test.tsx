import { render, screen, waitFor, act } from '@testing-library/react'
import { MemoryRouter, Routes, Route } from 'react-router-dom'
import { http, HttpResponse } from 'msw'
import { server } from '@/test/server'
import { AuthProvider } from '@/features/auth/context/AuthProvider'
import { tokenStorage } from '@/shared/services/tokenStorage'
import { useLogout } from './useLogout'

function LogoutButton() {
  const { logout, isLoading } = useLogout()
  return (
    <button onClick={() => void logout()} disabled={isLoading}>
      Cerrar sesión
    </button>
  )
}

function Wrapper() {
  return (
    <AuthProvider>
      <MemoryRouter initialEntries={['/dashboard']}>
        <Routes>
          <Route path="/dashboard" element={<LogoutButton />} />
          <Route path="/login" element={<div>Login Page</div>} />
        </Routes>
      </MemoryRouter>
    </AuthProvider>
  )
}

describe('useLogout', () => {
  it('calls logout endpoint, clears tokens, and navigates to /login', async () => {
    tokenStorage.setAccessToken('some-token')
    tokenStorage.setRefreshToken('some-refresh')

    render(<Wrapper />)

    await act(async () => {
      screen.getByRole('button', { name: /cerrar sesión/i }).click()
    })

    await waitFor(() => {
      expect(screen.getByText('Login Page')).toBeInTheDocument()
    })
    expect(tokenStorage.getAccessToken()).toBeNull()
    expect(tokenStorage.getRefreshToken()).toBeNull()
  })

  it('still clears tokens and navigates even when logout request fails (network error)', async () => {
    server.use(
      http.post('/api/auth/logout', () => HttpResponse.error()),
    )

    tokenStorage.setAccessToken('some-token')
    tokenStorage.setRefreshToken('some-refresh')

    render(<Wrapper />)

    await act(async () => {
      screen.getByRole('button', { name: /cerrar sesión/i }).click()
    })

    await waitFor(() => {
      expect(screen.getByText('Login Page')).toBeInTheDocument()
    })
    expect(tokenStorage.getAccessToken()).toBeNull()
  })
})
