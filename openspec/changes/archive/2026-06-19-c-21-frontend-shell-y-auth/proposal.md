## Why

Todo el backend (C-01→C-20) está operativo pero no existe interfaz de usuario. C-21 establece el shell SPA común — el esqueleto React sobre el que se montan todas las features del frontend (C-22/23/24) — incluyendo la capa de autenticación de la sesión en el cliente: login, 2FA, recuperación de contraseña, guard de rutas y cliente HTTP con refresh transparente de tokens.

## What Changes

- Scaffolding React 18 + TypeScript + Vite con estructura feature-based (`features/{dominio}/{components,hooks,services,types,pages}`) y carpeta `shared/`.
- Cliente HTTP centralizado (`shared/services/api.ts`, Axios): interceptor JWT automático, **refresh transparente** en cada 401 (sin que el componente lo sepa), manejo unificado de 403.
- Screens de autenticación: login (email + password), segundo factor TOTP, recuperación de contraseña (solicitar token + establecer nueva password).
- `AuthGuard` de rutas: redirige a login si no hay sesión válida; deniega con mensaje de error si hay sesión pero falta permiso.
- Layout raíz con menú lateral/superior adaptado a los permisos de la sesión activa (links visibles = permisos presentes).
- Logout explícito: revoca refresh token en el backend, limpia estado local.
- Configuración de TanStack Query (QueryClient global), React Hook Form + Zod listos para usar en features.
- Tests: render de pantalla de login, flujo de autenticación con mocks, guard redirige sin sesión, refresh transparente mantiene request original.

## Capabilities

### New Capabilities
- `frontend-shell`: Scaffolding SPA, estructura de directorios feature-based, QueryClient global, Tailwind, configuración de Vite y TypeScript.
- `auth-ui`: Pantallas de login / 2FA / recuperación, cliente HTTP con interceptor JWT+refresh, AuthGuard de rutas, layout adaptado a permisos, logout.

### Modified Capabilities
<!-- ninguna — C-21 es greenfield; no toca specs de backend -->

## Impact

- **Nuevo directorio**: `frontend/` (todo greenfield).
- **Consume backend**: `POST /api/auth/login`, `POST /api/auth/refresh`, `POST /api/auth/logout`, `POST /api/auth/forgot`, `POST /api/auth/reset`, `POST /api/auth/2fa/verify` (C-03); endpoint de permisos del usuario autenticado (C-04).
- **No toca backend**: ningún modelo, migración ni endpoint existente cambia.
- **Dependencias de runtime**: React 18, TypeScript 5, Vite 5, Tailwind CSS 3, TanStack Query v5, React Hook Form 7, Zod 3, Axios 1.x, React Router v6.
- **Dependencias de tests**: Vitest + Testing Library.
