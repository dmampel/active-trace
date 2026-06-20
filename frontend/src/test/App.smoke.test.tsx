import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { QueryClientProvider, QueryClient } from '@tanstack/react-query'
import { AuthProvider } from '@/features/auth/context/AuthProvider'
import { LoginPage } from '@/features/auth/pages/LoginPage'

const testQueryClient = new QueryClient({
  defaultOptions: { queries: { retry: false } },
})

function TestWrapper({ children }: { children: React.ReactNode }) {
  return (
    <QueryClientProvider client={testQueryClient}>
      <AuthProvider>
        <MemoryRouter>{children}</MemoryRouter>
      </AuthProvider>
    </QueryClientProvider>
  )
}

describe('Smoke test', () => {
  it('renders LoginPage without crashing', () => {
    render(
      <TestWrapper>
        <LoginPage />
      </TestWrapper>,
    )
    expect(screen.getByRole('button', { name: /ingresar/i })).toBeInTheDocument()
  })
})
