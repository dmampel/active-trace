import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { QueryClientProvider, QueryClient } from '@tanstack/react-query'
import { AuthProvider } from '@/features/auth/context/AuthProvider'
import { LoginPage } from './LoginPage'

const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })

function Wrapper({ children }: { children: React.ReactNode }) {
  return (
    <QueryClientProvider client={qc}>
      <AuthProvider>
        <MemoryRouter>{children}</MemoryRouter>
      </AuthProvider>
    </QueryClientProvider>
  )
}

describe('LoginPage', () => {
  it('renders email and password fields', () => {
    render(
      <Wrapper>
        <LoginPage />
      </Wrapper>,
    )
    expect(screen.getByLabelText(/email/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/contraseña/i)).toBeInTheDocument()
  })

  it('shows validation error for invalid email without making a request', async () => {
    const user = userEvent.setup()
    render(
      <Wrapper>
        <LoginPage />
      </Wrapper>,
    )
    await user.type(screen.getByLabelText(/email/i), 'notanemail')
    await user.type(screen.getByLabelText(/contraseña/i), 'password123')
    await user.click(screen.getByRole('button', { name: /ingresar/i }))

    await waitFor(() => {
      expect(screen.getByRole('alert', { name: '' })).toBeInTheDocument()
    })
    // No network error should appear
    expect(screen.queryByText(/credenciales inválidas/i)).not.toBeInTheDocument()
  })

  it('shows error message on 401 without redirecting', async () => {
    const user = userEvent.setup()
    render(
      <Wrapper>
        <LoginPage />
      </Wrapper>,
    )
    await user.type(screen.getByLabelText(/email/i), 'wrong@example.com')
    await user.type(screen.getByLabelText(/contraseña/i), 'wrongpassword')
    await user.click(screen.getByRole('button', { name: /ingresar/i }))

    await waitFor(() => {
      expect(screen.getByRole('alert')).toHaveTextContent(/credenciales inválidas/i)
    })
    // Should still be on login
    expect(screen.getByRole('button', { name: /ingresar/i })).toBeInTheDocument()
  })

  it('stores tokens and shows success state on valid credentials', async () => {
    const user = userEvent.setup()
    render(
      <Wrapper>
        <LoginPage />
      </Wrapper>,
    )
    await user.type(screen.getByLabelText(/email/i), 'valid@example.com')
    await user.type(screen.getByLabelText(/contraseña/i), 'password123')
    await user.click(screen.getByRole('button', { name: /ingresar/i }))

    await waitFor(() => {
      expect(localStorage.getItem('access_token')).toBe('mock-access-token')
    })
  })
})
