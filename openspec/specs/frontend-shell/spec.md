## ADDED Requirements

### Requirement: Proyecto React SPA con estructura feature-based
El sistema SHALL inicializar el proyecto frontend como una Single Page Application con React 18, TypeScript 5 y Vite 5 en el directorio `frontend/`. La estructura de directorios SHALL seguir el patrón feature-based canónico del proyecto: `src/features/{dominio}/{components,hooks,services,types,pages}/` y `src/shared/{services,components,hooks}/`.

#### Scenario: Estructura de directorios existe tras el scaffold
- **WHEN** se inicializa el proyecto frontend
- **THEN** existen los directorios `src/features/`, `src/shared/services/`, `src/shared/components/`, `src/shared/hooks/`

#### Scenario: TypeScript no acepta `any` implícito
- **WHEN** se compila el proyecto con `tsc --noEmit`
- **THEN** el compilador rechaza cualquier uso de `any` implícito (strict mode habilitado)

### Requirement: Configuración de TanStack Query global
El sistema SHALL proveer un `QueryClient` global configurado en el entry point de la aplicación, disponible para todas las features via el `QueryClientProvider` de TanStack Query v5.

#### Scenario: QueryClient disponible en toda la app
- **WHEN** un componente dentro de cualquier feature usa `useQuery` o `useMutation`
- **THEN** el hook resuelve sin error de contexto (QueryClientProvider presente en el árbol)

### Requirement: Tailwind CSS disponible sin configuración adicional
El sistema SHALL configurar Tailwind CSS 3 como único sistema de estilos. No SHALL existir CSS modules ni estilos globales inline (salvo valores dinámicos).

#### Scenario: Clases Tailwind se aplican en build de producción
- **WHEN** se genera el build de producción (`vite build`)
- **THEN** el CSS de salida contiene solo las clases Tailwind utilizadas (purge activo)

### Requirement: Tests de unidad con Vitest + Testing Library
El sistema SHALL configurar Vitest como runner de tests y `@testing-library/react` para rendering de componentes. La suite SHALL ejecutarse con `npm test` o `vitest run`.

#### Scenario: Test de humo pasa sin configuración adicional
- **WHEN** se ejecuta `vitest run` en el directorio `frontend/`
- **THEN** al menos un test de humo pasa sin error de configuración

### Requirement: Scripts npm estándar
El proyecto SHALL exponer los siguientes scripts en `package.json`: `dev` (servidor de desarrollo), `build` (producción), `test` (vitest run), `typecheck` (tsc --noEmit).

#### Scenario: Script `dev` inicia el servidor de desarrollo
- **WHEN** se ejecuta `npm run dev`
- **THEN** el servidor de desarrollo Vite arranca en el puerto configurado sin errores de compilación

#### Scenario: Script `build` genera artefacto de producción
- **WHEN** se ejecuta `npm run build`
- **THEN** el directorio `dist/` se genera con el bundle de producción
