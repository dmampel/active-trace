import { http, HttpResponse } from 'msw'

const mockUser = {
  id: '1',
  email: 'prof@example.com',
  nombre: 'María',
  apellido: 'González',
  roles: ['PROFESOR'],
  permissions: ['comisiones:read', 'alumnos:read'],
}

export const handlers = [
  // Login — success
  http.post('/api/auth/login', async ({ request }) => {
    const body = await request.json() as { email: string; password: string }
    if (body.email === 'valid@example.com' && body.password === 'password123') {
      return HttpResponse.json({
        access_token: 'mock-access-token',
        refresh_token: 'mock-refresh-token',
        user: mockUser,
      })
    }
    if (body.email === '2fa@example.com') {
      return HttpResponse.json({ status: '2fa_required', temp_token: 'mock-temp-token' })
    }
    return HttpResponse.json({ detail: 'Credenciales inválidas' }, { status: 401 })
  }),

  // Refresh — success
  http.post('/api/auth/refresh', () => {
    return HttpResponse.json({
      access_token: 'new-access-token',
      refresh_token: 'new-refresh-token',
    })
  }),

  // Logout
  http.post('/api/auth/logout', () => {
    return HttpResponse.json({ ok: true })
  }),

  // Forgot password
  http.post('/api/auth/forgot', () => {
    return HttpResponse.json({ ok: true })
  }),

  // Reset password
  http.post('/api/auth/reset', () => {
    return HttpResponse.json({ ok: true })
  }),

  // 2FA verify
  http.post('/api/auth/2fa/verify', () => {
    return HttpResponse.json({
      access_token: 'mock-access-token',
      refresh_token: 'mock-refresh-token',
      user: mockUser,
    })
  }),
]
