import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { ForgotPasswordPage } from './ForgotPasswordPage'

function Wrapper({ children }: { children: React.ReactNode }) {
  return <MemoryRouter>{children}</MemoryRouter>
}

describe('ForgotPasswordPage', () => {
  it('calls POST /api/auth/forgot and shows confirmation message', async () => {
    const user = userEvent.setup()
    render(
      <Wrapper>
        <ForgotPasswordPage />
      </Wrapper>,
    )

    await user.type(screen.getByLabelText(/email/i), 'user@example.com')
    await user.click(screen.getByRole('button', { name: /enviar enlace/i }))

    await waitFor(() => {
      expect(screen.getByText(/revisá tu casilla/i)).toBeInTheDocument()
    })
  })

  it('shows generic confirmation even if email does not exist (anti-enumeration)', async () => {
    const user = userEvent.setup()
    render(
      <Wrapper>
        <ForgotPasswordPage />
      </Wrapper>,
    )

    await user.type(screen.getByLabelText(/email/i), 'nonexistent@example.com')
    await user.click(screen.getByRole('button', { name: /enviar enlace/i }))

    await waitFor(() => {
      expect(screen.getByText(/revisá tu casilla/i)).toBeInTheDocument()
    })
  })
})
