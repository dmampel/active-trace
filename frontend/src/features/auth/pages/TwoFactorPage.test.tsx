import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { QueryClientProvider, QueryClient } from '@tanstack/react-query'
import { AuthProvider } from '@/features/auth/context/AuthProvider'
import { http, HttpResponse } from 'msw'
import { server } from '@/test/server'
import { TwoFactorPage } from './TwoFactorPage'

const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })

function Wrapper({ children }: { children: React.ReactNode }) {
  return (
    <QueryClientProvider client={qc}>
      <AuthProvider>
        <MemoryRouter initialEntries={[{ pathname: '/login/2fa', state: { temp_token: 'test-temp' } }]}>
          {children}
        </MemoryRouter>
      </AuthProvider>
    </QueryClientProvider>
  )
}

describe('TwoFactorPage', () => {
  it('persists tokens and redirects on valid code', async () => {
    const user = userEvent.setup()
    render(
      <Wrapper>
        <TwoFactorPage />
      </Wrapper>,
    )

    // Type 6 digits — auto-submit triggers
    await user.type(screen.getByLabelText(/código/i), '123456')

    await waitFor(() => {
      expect(localStorage.getItem('access_token')).toBe('mock-access-token')
    })
  })

  it('shows error and stays on page when code is incorrect', async () => {
    server.use(
      http.post('/api/auth/2fa/verify', () => new HttpResponse(null, { status: 401 })),
    )

    const user = userEvent.setup()
    render(
      <Wrapper>
        <TwoFactorPage />
      </Wrapper>,
    )

    await user.type(screen.getByLabelText(/código/i), '999999')

    await waitFor(() => {
      expect(screen.getByRole('alert')).toHaveTextContent(/código incorrecto/i)
    })
    // Still on 2FA page
    expect(screen.getByLabelText(/código/i)).toBeInTheDocument()
  })
})
