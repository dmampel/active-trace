## Context

Todo el backend de activia-trace (C-01→C-20, ~570 tests) está operativo. No existe frontend. C-21 es el punto de entrada de la capa de presentación: crea el proyecto React, la infraestructura compartida (cliente HTTP, estado de auth, guards) y las cuatro pantallas del flujo de autenticación. Los changes C-22/23/24 se montan encima de este shell sin necesidad de retroceder.

El backend ya expone los endpoints de autenticación (C-03): `/api/auth/login`, `/api/auth/refresh`, `/api/auth/logout`, `/api/auth/forgot`, `/api/auth/reset`, y los de verificación de 2FA. La API usa JWT (access 15min + refresh con rotación).

## Goals / Non-Goals

**Goals:**
- Proyecto React 18 + TypeScript + Vite funcional con estructura feature-based canónica.
- Cliente HTTP centralizado con refresh transparente de tokens (el componente no sabe que hubo un 401).
- Pantallas: login, 2FA TOTP, solicitar recuperación, establecer nueva contraseña.
- `AuthGuard` que redirige a `/login` si no hay sesión y muestra 403 si falta permiso.
- Layout raíz con menú adaptado a los permisos de la sesión activa.
- Suite de tests mínima: login render, mock auth flow, guard sin sesión, refresh transparente.
- Configuración lista para que C-22/23/24 agreguen features sin tocar la infraestructura.

**Non-Goals:**
- Ninguna pantalla de dominio (atrasados, equipos, liquidaciones, auditoría) — eso es C-22/23/24.
- Dark mode, i18n, feature flags.
- PWA / Service Workers.
- Websockets (el backend no los expone en el MVP).

## Decisions

### D-01 — Almacenamiento de tokens: `httpOnly` cookies vs. `localStorage`

**Decisión**: `localStorage` (access token) + `localStorage` (refresh token), con XSS mitigation via CSP estricta.

**Por qué no httpOnly cookies**: el backend FastAPI ya usa Authorization Bearer en todos los endpoints. Cambiar a cookies requeriría modificar middleware de CORS y CSRF en el backend (fuera del scope de C-21). En el MVP, el riesgo XSS se mitiga vía CSP; si en el futuro se decide mover a cookies, el cambio es local al cliente HTTP.

**Alternativa descartada**: `sessionStorage` — se pierde en nueva pestaña, lo que rompe UX para trabajo multi-pestaña docente.

### D-02 — Refresh transparente: cola de reintentos mientras se refresca

**Decisión**: interceptor de respuesta Axios que, ante un 401:
1. Pausa y encola los requests fallidos (array de `{ resolve, reject }`).
2. Si no hay un refresh en curso, lanza `POST /api/auth/refresh`.
3. Al completarse, resuelve toda la cola con el nuevo access token.
4. Si el refresh falla (refresh expirado o revocado), rechaza toda la cola y redirige a `/login`.

Este patrón evita race conditions donde múltiples requests concurrentes lanzarían el refresh en paralelo. Implementación en `shared/services/api.ts`.

### D-03 — Server state: TanStack Query v5

**Decisión**: TanStack Query para todos los fetches. No se usa Zustand ni Redux para server state.

**Por qué**: el dominio de activia-trace es altamente relacional (docente → comisión → alumnos → calificaciones) y la invalidación de caché dirigida por query key es más expresiva que un store global. TanStack Query ya está en el stack canónico del proyecto.

**Estado local de auth** (tokens, usuario, permisos) vive en un `AuthContext` React (no en TanStack Query) porque es sincrónico y no paginable.

### D-04 — Routing: React Router v6 con lazy loading por feature

**Decisión**: `createBrowserRouter` + `lazy()` en cada feature page. El guard se implementa como wrapper component (`<AuthGuard requiredPermission="...">`) que envuelve cada route element.

Las rutas de C-22/23/24 se agregan en su propio change sin modificar las rutas de auth.

### D-05 — Testing: Vitest + Testing Library

**Decisión**: Vitest (integrado con Vite, sin configuración extra) + `@testing-library/react` + `msw` para mock de la API.

**Por qué no Jest**: Jest requiere transformers adicionales para ES modules y Vite. Vitest usa la misma config de Vite y tiene API compatible. `msw` (Mock Service Worker) permite mockear la red al nivel de fetch/axios sin parchear módulos — los tests de refresh son confiables.

### D-06 — Menú adaptado a permisos

**Decisión**: el `AuthContext` expone un helper `hasPermission(perm: string): boolean` derivado del array de permisos del usuario en sesión. El componente de menú usa `hasPermission` para decidir qué links renderizar. Los permisos se obtienen del backend tras el login (endpoint de perfil / me) y se cachean en el contexto.

No se guardan permisos en el JWT (el backend no lo hace) — se obtienen con un GET al endpoint de usuario autenticado.

## Risks / Trade-offs

- **Tokens en localStorage + XSS**: requiere CSP header estricta (`script-src 'self'`). Sin CSP configurada en el servidor, un script inyectado puede robar el token. Mitigación: configurar CSP en el `vite.config.ts` (dev) y en el proxy/Easypanel (producción) desde el inicio de C-21.

- **Refresh race condition**: el patrón de cola (D-02) resuelve el caso más común (múltiples tabs no están sincronizadas entre sí). Si el usuario tiene múltiples pestañas abiertas, cada pestaña puede intentar su propio refresh. Mitigación: el backend invalida el refresh anterior en rotación — la pestaña que pierde la carrera obtiene un 401 en el refresh y redirige a login. Comportamiento aceptable en MVP.

- **Permisos desactualizados en sesión**: si un ADMIN revoca un rol mientras el usuario tiene sesión activa, los permisos en `AuthContext` quedan obsoletos hasta el próximo refresh del access token. Mitigación: re-fetch del endpoint `/api/auth/me` (o equivalente) tras cada renovación de token.

## Migration Plan

Greenfield — no hay código previo que migrar. Plan de deploy:

1. `frontend/` se agrega como nuevo directorio en el repo.
2. `docker-compose.yml` existente se extiende con el servicio `frontend` (Vite dev server en local; build estático servido por nginx en producción).
3. No requiere rollback de backend — el backend no cambia.

## Open Questions

- **¿Endpoint de permisos del usuario?** El backend expone `GET /api/perfil` (C-20) que devuelve datos del usuario. ¿Incluye el array de permisos efectivos o hay que agregar un campo? → Verificar respuesta de `/api/perfil` antes de implementar D-06; si no incluye permisos, agregar un `GET /api/auth/me` mínimo en el backend (cambio pequeño, fuera del scope pero necesario).

- **Dominio del cookie de refresh** (si en el futuro se migra a httpOnly cookie): pendiente de definición de dominios de producción en Easypanel.
