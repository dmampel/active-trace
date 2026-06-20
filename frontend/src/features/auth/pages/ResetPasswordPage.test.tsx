import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Routes, Route } from 'react-router-dom'
import { ResetPasswordPage } from './ResetPasswordPage'

function WrapperWithToken({ children }: { children: React.ReactNode }) {
  return (
    <MemoryRouter initialEntries={['/reset-password?token=valid-token']}>
      <Routes>
        <Route path="/reset-password" element={children} />
        <Route path="/login" element={<div>Login Page</div>} />
      </Routes>
    </MemoryRouter>
  )
}

describe('ResetPasswordPage', () => {
  it('shows validation error when passwords do not match (no network request)', async () => {
    const user = userEvent.setup()
    render(
      <WrapperWithToken>
        <ResetPasswordPage />
      </WrapperWithToken>,
    )

    await user.type(screen.getByLabelText(/nueva contraseña/i), 'Password123')
    await user.type(screen.getByLabelText(/confirmar/i), 'DifferentPass')
    await user.click(screen.getByRole('button', { name: /cambiar/i }))

    await waitFor(() => {
      expect(screen.getByRole('alert')).toHaveTextContent(/no coinciden/i)
    })
    // Not navigated away
    expect(screen.queryByText('Login Page')).not.toBeInTheDocument()
  })

  it('redirects to /login after successful reset', async () => {
    const user = userEvent.setup()
    render(
      <WrapperWithToken>
        <ResetPasswordPage />
      </WrapperWithToken>,
    )

    await user.type(screen.getByLabelText(/nueva contraseña/i), 'NewPassword1')
    await user.type(screen.getByLabelText(/confirmar/i), 'NewPassword1')
    await user.click(screen.getByRole('button', { name: /cambiar/i }))

    await waitFor(() => {
      expect(screen.getByText('Login Page')).toBeInTheDocument()
    })
  })
})
