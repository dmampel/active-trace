## 1. Scaffold del proyecto React

- [x] 1.1 Crear el proyecto con `npm create vite@latest frontend -- --template react-ts` en la raíz del repo
- [x] 1.2 Instalar dependencias de producción: `axios`, `@tanstack/react-query@5`, `react-hook-form`, `zod`, `@hookform/resolvers`, `react-router-dom@6`
- [x] 1.3 Instalar Tailwind CSS 3 y configurar `tailwind.config.ts` con los paths de `src/`
- [x] 1.4 Configurar `tsconfig.json` con `strict: true`, `noImplicitAny: true`, alias `@/` → `src/`
- [x] 1.5 Configurar `vite.config.ts` con el alias `@` y proxy de la API al backend (`/api` → `http://localhost:8000`)
- [x] 1.6 Crear la estructura de directorios: `src/features/`, `src/shared/services/`, `src/shared/components/`, `src/shared/hooks/`, `src/shared/types/`
- [x] 1.7 Instalar dependencias de test: `vitest`, `@testing-library/react`, `@testing-library/user-event`, `@testing-library/jest-dom`, `msw`, `happy-dom`
- [x] 1.8 Configurar Vitest en `vite.config.ts` (environment `happy-dom`, setup file con `@testing-library/jest-dom`)
- [x] 1.9 Agregar scripts en `package.json`: `dev`, `build`, `test`, `typecheck`
- [x] 1.10 Escribir test de humo: verificar que `<App />` renderiza sin errores

## 2. AuthContext y almacenamiento de tokens

- [x] 2.1 Definir tipos en `src/shared/types/auth.ts`: `User`, `Session`, `AuthContextValue`, `PermissionString`
- [x] 2.2 Crear `src/shared/services/tokenStorage.ts`: get/set/clear para `access_token` y `refresh_token` en `localStorage`
- [x] 2.3 Crear `src/features/auth/context/AuthContext.tsx` con: `user`, `session`, `isAuthenticated`, `hasPermission(perm)`, `setSession()`, `clearSession()`
- [x] 2.4 Crear `src/features/auth/context/AuthProvider.tsx`: inicializa el contexto desde `localStorage` en el mount, expone `AuthContext`
- [x] 2.5 Montar `AuthProvider` en `src/main.tsx` (raíz del árbol)
- [x] 2.6 Test: `hasPermission` retorna `true` con permiso en sesión y `false` sin él

## 3. Cliente HTTP centralizado con refresh transparente

- [x] 3.1 Crear `src/shared/services/api.ts`: instancia Axios con `baseURL: '/api'` y `Content-Type: application/json`
- [x] 3.2 Interceptor de request: adjunta `Authorization: Bearer <access_token>` desde `tokenStorage`
- [x] 3.3 Implementar la cola de reintentos (`pendingRequests: Array<{resolve, reject}>`) y el flag `isRefreshing`
- [x] 3.4 Interceptor de response: ante 401, encola el request, lanza `POST /api/auth/refresh` (una sola vez), resuelve la cola con el nuevo token o rechaza y llama `clearSession()` + `window.location = '/login'`
- [x] 3.5 Test: un 401 dispara el refresh y reintenta el request original (usando msw)
- [x] 3.6 Test: dos 401 concurrentes emiten solo un refresh y ambos requests se resuelven con el nuevo token
- [x] 3.7 Test: refresh fallido limpia storage y redirige a `/login`

## 4. Routing y layout raíz

- [x] 4.1 Crear `src/app/router.tsx` con `createBrowserRouter`: rutas públicas (`/login`, `/login/2fa`, `/forgot-password`, `/reset-password`) y ruta raíz protegida con outlet
- [x] 4.2 Crear `src/features/auth/components/AuthGuard.tsx`: comprueba `isAuthenticated`; si no → `<Navigate to="/login" state={{ from: location }} />`; si hay `requiredPermission` y no lo tiene → renderiza `<Forbidden />`
- [x] 4.3 Crear `src/shared/components/Forbidden.tsx`: pantalla 403 con mensaje de acceso denegado
- [x] 4.4 Crear `src/shared/components/AppLayout.tsx`: barra lateral / header con menú filtrado por `hasPermission`
- [x] 4.5 Definir los items del menú con su `permission` requerido y el `path` de destino (feature-flag driven)
- [x] 4.6 Test: `AuthGuard` sin sesión renderiza `<Navigate to="/login" />`
- [x] 4.7 Test: `AuthGuard` con sesión pero sin permiso renderiza `<Forbidden />`
- [x] 4.8 Test: `AuthGuard` con sesión y permiso correcto renderiza el children

## 5. Pantalla de login

- [x] 5.1 Crear `src/features/auth/pages/LoginPage.tsx` con formulario React Hook Form + schema Zod (`email`, `password`)
- [x] 5.2 Crear `src/features/auth/services/authApi.ts`: funciones `login()`, `refresh()`, `logout()`, `forgotPassword()`, `resetPassword()`, `verify2fa()` usando el cliente centralizado
- [x] 5.3 Crear hook `src/features/auth/hooks/useLogin.ts`: llama a `authApi.login()`, persiste tokens, actualiza `AuthContext`, detecta respuesta `2fa_required` y navega a `/login/2fa`
- [x] 5.4 Conectar `useLogin` con `LoginPage`; manejar estado de loading y error en UI
- [x] 5.5 Al login exitoso, redirigir a la ruta guardada por `AuthGuard` (`state.from`) o a `/`
- [x] 5.6 Test: render de `LoginPage` muestra campos email y password
- [x] 5.7 Test: submit con credenciales válidas (msw) guarda tokens y redirige
- [x] 5.8 Test: submit con 401 muestra mensaje de error sin redirigir
- [x] 5.9 Test: email inválido muestra error de validación Zod sin request al backend

## 6. Pantalla de segundo factor (2FA)

- [x] 6.1 Crear `src/features/auth/pages/TwoFactorPage.tsx` con campo de código TOTP (6 dígitos, auto-submit)
- [x] 6.2 Crear hook `useVerify2fa.ts`: llama a `authApi.verify2fa(tempToken, code)`, persiste tokens y navega a `/`
- [x] 6.3 Test: código correcto (msw) persiste tokens y redirige a `/`
- [x] 6.4 Test: código incorrecto muestra error y permanece en la pantalla 2FA

## 7. Flujo de recuperación de contraseña

- [x] 7.1 Crear `src/features/auth/pages/ForgotPasswordPage.tsx` con campo email y hook `useForgotPassword.ts`
- [x] 7.2 Mostrar mensaje de confirmación genérico al éxito (sin revelar existencia del email)
- [x] 7.3 Crear `src/features/auth/pages/ResetPasswordPage.tsx`: lee `token` del query string; campos `password` + `confirmPassword` validados con Zod
- [x] 7.4 Al reset exitoso redirigir a `/login` con mensaje de éxito (query param o toast)
- [x] 7.5 Test: submit en ForgotPasswordPage llama a `POST /api/auth/forgot` y muestra confirmación
- [x] 7.6 Test: passwords no coinciden en ResetPasswordPage muestran error Zod sin request

## 8. Logout

- [x] 8.1 Agregar acción de logout en `AppLayout` (botón / menú de usuario)
- [x] 8.2 Crear hook `useLogout.ts`: llama a `authApi.logout()` (best-effort), limpia storage via `tokenStorage.clear()`, llama a `clearSession()` del `AuthContext` y navega a `/login`
- [x] 8.3 Test: logout llama al endpoint, limpia tokens y navega a `/login`
- [x] 8.4 Test: logout con error de red igual limpia tokens locales y navega a `/login`

## 9. Integración final y configuración Docker

- [x] 9.1 Verificar que `npm run typecheck` pasa sin errores (`any` implícito = error)
- [x] 9.2 Verificar que `npm test` ejecuta todos los tests y pasan
- [x] 9.3 Verificar que `npm run build` genera `dist/` sin errores
- [x] 9.4 Agregar el servicio `frontend` al `docker-compose.yml` del repo: Vite dev server en local (`npm run dev`) con el puerto expuesto
- [x] 9.5 Crear `frontend/Dockerfile` multi-stage: stage `build` (node + npm run build), stage `serve` (nginx con el `dist/`)
- [ ] 9.6 Marcar `[x]` en [CHANGES.md](../../../../CHANGES.md) para C-21 una vez archivado
