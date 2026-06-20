import axios, { type AxiosRequestConfig, type InternalAxiosRequestConfig } from 'axios'
import { tokenStorage } from './tokenStorage'

export const apiClient = axios.create({
  baseURL: '/api/v1',
  headers: {
    'Content-Type': 'application/json',
  },
})

// --- Refresh queue state (module-level, shared across all interceptor calls) ---
let isRefreshing = false
type QueueItem = { resolve: (token: string) => void; reject: (err: unknown) => void }
let pendingRequests: QueueItem[] = []

function resolveQueue(newToken: string): void {
  pendingRequests.forEach(({ resolve }) => resolve(newToken))
  pendingRequests = []
}

function rejectQueue(err: unknown): void {
  pendingRequests.forEach(({ reject }) => reject(err))
  pendingRequests = []
}

// Marker to avoid intercepting the refresh request itself
const SKIP_REFRESH_HEADER = 'x-skip-refresh-interceptor'

// --- Request interceptor: attach Authorization + X-Tenant-ID headers ---
apiClient.interceptors.request.use((config: InternalAxiosRequestConfig) => {
  const token = tokenStorage.getAccessToken()
  if (token) {
    config.headers['Authorization'] = `Bearer ${token}`
  }
  const tenantId = tokenStorage.getTenantId()
  if (tenantId) {
    config.headers['X-Tenant-ID'] = tenantId
  }
  return config
})

// --- Response interceptor: transparent refresh on 401 ---
apiClient.interceptors.response.use(
  (response) => response,
  async (error: unknown) => {
    if (!axios.isAxiosError(error) || !error.config || error.response?.status !== 401) {
      return Promise.reject(error)
    }

    const originalRequest = error.config as AxiosRequestConfig & { headers: Record<string, string> }

    // Avoid infinite loop: skip interceptor for auth endpoints (login, refresh, forgot, reset)
    const requestUrl = originalRequest.url ?? ''
    const isAuthEndpoint = requestUrl.includes('/auth/')
    if (isAuthEndpoint || originalRequest.headers?.[SKIP_REFRESH_HEADER]) {
      if (requestUrl.includes('/auth/refresh')) {
        // Refresh failed: clear tokens and redirect
        tokenStorage.clear()
        window.location.href = '/login'
      }
      return Promise.reject(error)
    }

    if (isRefreshing) {
      // Queue this request until the refresh completes
      return new Promise((resolve, reject) => {
        pendingRequests.push({
          resolve: (token: string) => {
            originalRequest.headers['Authorization'] = `Bearer ${token}`
            resolve(apiClient(originalRequest))
          },
          reject,
        })
      })
    }

    isRefreshing = true

    try {
      const refreshToken = tokenStorage.getRefreshToken()
      const { data } = await apiClient.post<{ access_token: string; refresh_token: string }>(
        '/auth/refresh',
        { refresh_token: refreshToken },
        { headers: { [SKIP_REFRESH_HEADER]: '1' } },
      )

      tokenStorage.setAccessToken(data.access_token)
      tokenStorage.setRefreshToken(data.refresh_token)
      originalRequest.headers['Authorization'] = `Bearer ${data.access_token}`

      resolveQueue(data.access_token)
      return apiClient(originalRequest)
    } catch (refreshError) {
      rejectQueue(refreshError)
      tokenStorage.clear()
      window.location.href = '/login'
      return Promise.reject(refreshError)
    } finally {
      isRefreshing = false
    }
  },
)
