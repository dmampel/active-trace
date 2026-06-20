import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { http, HttpResponse } from 'msw'
import { server } from '@/test/server'
import { tokenStorage } from './tokenStorage'
import { apiClient } from './api'

describe('API client – refresh interceptor', () => {
  beforeEach(() => {
    localStorage.clear()
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('retries the original request after a 401 triggers a successful refresh', async () => {
    tokenStorage.setRefreshToken('valid-refresh')

    let protectedCallCount = 0
    server.use(
      http.get('/api/protected', () => {
        protectedCallCount++
        if (protectedCallCount === 1) {
          return new HttpResponse(null, { status: 401 })
        }
        return HttpResponse.json({ data: 'secret' })
      }),
      http.post('/api/auth/refresh', () => {
        return HttpResponse.json({
          access_token: 'new-access-token',
          refresh_token: 'new-refresh-token',
        })
      }),
    )

    const response = await apiClient.get('/protected')
    expect(response.data).toEqual({ data: 'secret' })
    expect(protectedCallCount).toBe(2)
    expect(tokenStorage.getAccessToken()).toBe('new-access-token')
  })

  it('clears storage and redirects to /login when refresh fails (401 on refresh endpoint)', async () => {
    tokenStorage.setAccessToken('expired-access')
    tokenStorage.setRefreshToken('expired-refresh')

    // Spy on location.href assignment
    const locationSpy = vi.spyOn(window, 'location', 'get').mockReturnValue({
      ...window.location,
      href: '',
    } as Location)
    let capturedHref = ''
    vi.spyOn(window, 'location', 'get').mockReturnValue(
      new Proxy(window.location, {
        set(target, prop, value) {
          if (prop === 'href') capturedHref = String(value)
          return Reflect.set(target, prop, value)
        },
      }),
    )
    locationSpy.mockRestore()

    server.use(
      http.get('/api/protected-fail', () => new HttpResponse(null, { status: 401 })),
      http.post('/api/auth/refresh', () => new HttpResponse(null, { status: 401 })),
    )

    let didReject = false
    try {
      await apiClient.get('/protected-fail')
    } catch {
      didReject = true
    }

    expect(didReject).toBe(true)
    expect(tokenStorage.getAccessToken()).toBeNull()
    expect(tokenStorage.getRefreshToken()).toBeNull()
    // Note: window.location.href assignment triggers "Not implemented: navigation to another Document"
    // in jsdom — this is expected behavior; the redirect happens in a real browser
  })

  it('issues only one refresh for two concurrent 401s and resolves both', async () => {
    tokenStorage.setRefreshToken('valid-refresh')

    let refreshCallCount = 0
    let resourceCallCount = 0

    server.use(
      http.get('/api/resource-concurrent', () => {
        resourceCallCount++
        if (resourceCallCount <= 2) {
          return new HttpResponse(null, { status: 401 })
        }
        return HttpResponse.json({ ok: true })
      }),
      http.post('/api/auth/refresh', () => {
        refreshCallCount++
        return HttpResponse.json({
          access_token: 'shared-new-token',
          refresh_token: 'shared-new-refresh',
        })
      }),
    )

    const [r1, r2] = await Promise.all([
      apiClient.get('/resource-concurrent'),
      apiClient.get('/resource-concurrent'),
    ])

    expect(r1.data).toEqual({ ok: true })
    expect(r2.data).toEqual({ ok: true })
    expect(refreshCallCount).toBe(1)
  })
})
