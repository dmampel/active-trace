import { apiClient } from '@/shared/services/api'
import type { Session } from '@/shared/types/auth'

export interface LoginPayload {
  email: string
  password: string
}

export type LoginResponse =
  | { status: 'ok'; session: Session }
  | { status: '2fa_required'; temp_token: string }

export interface LoginRawResponse {
  status?: string
  temp_token?: string
  access_token?: string
  refresh_token?: string
  user?: Session['user']
}

export interface RefreshResponse {
  access_token: string
  refresh_token: string
}

export interface Verify2faPayload {
  temp_token: string
  code: string
}

export interface ForgotPasswordPayload {
  email: string
}

export interface ResetPasswordPayload {
  token: string
  password: string
}

async function login(payload: LoginPayload): Promise<LoginResponse> {
  const { data } = await apiClient.post<LoginRawResponse>('/auth/login', payload)

  if (data.status === '2fa_required' && data.temp_token) {
    return { status: '2fa_required', temp_token: data.temp_token }
  }

  if (data.access_token && data.refresh_token && data.user) {
    return {
      status: 'ok',
      session: {
        access_token: data.access_token,
        refresh_token: data.refresh_token,
        user: data.user,
      },
    }
  }

  throw new Error('Respuesta de login inesperada del servidor')
}

async function refresh(refreshToken: string): Promise<RefreshResponse> {
  const { data } = await apiClient.post<RefreshResponse>('/auth/refresh', {
    refresh_token: refreshToken,
  })
  return data
}

async function logout(): Promise<void> {
  await apiClient.post('/auth/logout')
}

async function forgotPassword(payload: ForgotPasswordPayload): Promise<void> {
  await apiClient.post('/auth/forgot', payload)
}

async function resetPassword(payload: ResetPasswordPayload): Promise<void> {
  await apiClient.post('/auth/reset', payload)
}

async function verify2fa(payload: Verify2faPayload): Promise<Session> {
  const { data } = await apiClient.post<{
    access_token: string
    refresh_token: string
    user: Session['user']
  }>('/auth/2fa/verify', payload)
  return {
    access_token: data.access_token,
    refresh_token: data.refresh_token,
    user: data.user,
  }
}

export const authApi = { login, refresh, logout, forgotPassword, resetPassword, verify2fa }
