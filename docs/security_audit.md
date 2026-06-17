# Auditoría de Seguridad - Activia Trace (Backend)

## Resumen Ejecutivo

El backend de Activia Trace demuestra fundamentos sólidos (uso de Argon2, AES-256-GCM para datos sensibles, validación de tenants obligatoria en consultas). Los tres hallazgos críticos del audit inicial fueron corregidos exitosamente. Este documento registra el estado actualizado e incluye nuevos hallazgos descubiertos en la revisión del código actual (C-08 equipos).

---

## ✅ Hallazgos Originales — Resueltos

### 1. Escalada de Privilegios vía Impersonación
**Estado: RESUELTO** — Se implementó `ROLE_HIERARCHY` + `_max_role_level()` en `auth_service.py`. Un usuario no puede impersonar a alguien con nivel de privilegio superior.

### 2. Ausencia de CORS
**Estado: RESUELTO** — `CORSMiddleware` configurado en `main.py` usando `settings.cors_origins` (configurable por entorno, default `localhost:3000`).

### 3. Fuerza de Contraseña en Reset
**Estado: RESUELTO** — `ResetPasswordRequest` tiene `min_length=12` + `@field_validator` que exige al menos una letra y un número.

---

## 🚨 Nuevos Hallazgos Críticos

### 4. IDOR en `asignacion_masiva` — Cross-Tenant User Assignment
**Severidad: ALTA**
**Archivo:** `backend/app/services/equipo_service.py` líneas 188-204
**Archivo:** `backend/app/repositories/asignacion_repository.py` líneas 150-170

**Problema:** El endpoint `POST /equipos/masiva` valida que el contexto (cohorte, materia, carrera) pertenezca al tenant, pero NO valida que los `usuario_ids` del body pertenezcan al mismo tenant. Un atacante con permiso `equipos:manage` puede enviar UUIDs de usuarios de otros tenants y crear asignaciones cross-tenant válidas.

```python
# equipo_service.py — SIN validación de tenant sobre usuario_ids
items = [
    {"usuario_id": uid, ...}   # uid viene del body sin verificar
    for uid in data.usuario_ids
]
await repo.bulk_create(tenant_id, items)  # FK a users.id pasa; tenant no se chequea
```

**La FK (`Asignacion.usuario_id → users.id`) no garantiza aislamiento** porque la tabla `users` contiene usuarios de todos los tenants diferenciados solo por `users.tenant_id`.

**Solución:** Antes de `bulk_create`, validar que todos los `usuario_ids` existan y pertenezcan al `current_user.tenant_id`:
```python
# En EquipoService.asignacion_masiva, antes de bulk_create:
stmt = select(func.count()).where(
    User.id.in_(data.usuario_ids),
    User.tenant_id == tenant_id,
    User.deleted_at.is_(None),
)
count = (await self.session.execute(stmt)).scalar_one()
if count != len(data.usuario_ids):
    raise HTTPException(status_code=422, detail="Uno o más usuario_ids no pertenecen al tenant")
```

---

## 🔴 Hallazgos de Severidad Alta

### 5. Information Leakage en `reset-password`
**Severidad: MEDIA-ALTA**
**Archivo:** `backend/app/api/v1/routers/auth.py` líneas 103-104

**Problema:** El error interno de `AuthService.reset_password` se expone directo al cliente. Mensajes como `"Reset token expired"`, `"Invalid or already used reset token"`, y `"Invalid reset token"` revelan información útil para un atacante (sabe cuándo el token expiró vs. cuándo ya fue usado).

```python
# INSEGURO — expone el mensaje interno
except AuthError as exc:
    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
```

Comparar con `login` que lo hace bien: `detail="Invalid credentials"`.

**Solución:** Normalizar el mensaje al cliente:
```python
except AuthError:
    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired reset token")
```

---

## 🟡 Hallazgos de Severidad Media

### 6. N+1 Queries en `mis_asignaciones`
**Severidad: MEDIA (Performance)**
**Archivo:** `backend/app/services/equipo_service.py` líneas 96-98

**Problema:** Por cada asignación retornada se hacen 3 queries DB separadas para resolver nombres de materia, carrera y cohorte. Con N asignaciones = 3N+1 queries.

```python
# Por cada asignación en el loop:
materia_nombre = await self._resolve_materia_nombre(a.materia_id)   # query 1
carrera_nombre = await self._resolve_carrera_nombre(a.carrera_id)   # query 2
cohorte_nombre = await self._resolve_cohorte_nombre(a.cohorte_id)   # query 3
```

**Solución:** Resolver los nombres en un solo JOIN desde el repositorio. Crear `list_for_usuario_con_nombres()` que use joins con Materia/Carrera/Cohorte.

### 7. `_resolve_*_nombre` No Filtra por `tenant_id`
**Severidad: MEDIA (Tenant Isolation Leak)**
**Archivo:** `backend/app/services/equipo_service.py` líneas 115-140

**Problema:** Las helpers `_resolve_materia_nombre`, `_resolve_carrera_nombre` y `_resolve_cohorte_nombre` hacen queries sin restricción de tenant. Si un atacante con token válido envía un UUID conocido de una entidad de otro tenant, puede inferir su nombre.

```python
# SIN filtro de tenant — puede retornar nombres de otros tenants
result = await self.session.execute(
    select(Materia.nombre).where(Materia.id == materia_id)
)
```

**Solución:** Agregar `Materia.tenant_id == self.current_user.tenant_id` a cada query.

### 8. `buscar_usuarios` Incluye Usuarios Inactivos
**Severidad: MEDIA (Data Integrity)**
**Archivo:** `backend/app/services/equipo_service.py` líneas 149-157

**Problema:** El filtro usa `User.deleted_at.is_(None)` pero no filtra por `User.is_active`. Usuarios suspendidos/inactivos (que no deben ser asignables) aparecen en el autocompletado de asignación masiva.

**Solución:** Agregar `User.is_active == True` al where clause.

---

## 🟢 Hallazgos de Severidad Baja

### 9. `end_impersonation` No Invalida el Token
**Severidad: BAJA**
**Archivo:** `backend/app/api/v1/routers/auth.py` líneas 174-185

**Problema:** El endpoint solo registra auditoría pero el token de impersonación (JWT) sigue siendo válido hasta su expiración (default: 60 minutos). Si el token fue capturado, sigue usable después del "cierre" de sesión.

**Mitigación existente:** El token de impersonación tiene vida corta (60 min) y el `actor_id` del auditor se registra en cada acción. Sin revocación de JWT no hay solución perfecta sin lista negra.

**Solución a mediano plazo:** Implementar una allowlist/blocklist de JTI (JWT ID) para tokens de impersonación en Redis, con TTL igual al `impersonation_token_expire_minutes`. Agregar `jti` claim al crear el token y verificarlo en `get_current_user`.

### 10. Discrepancia en Derivación de Clave AES
**Severidad: BAJA (Risk: future bugs)**
**Archivos:** `auth_service.py` líneas 47-49 vs `usuario_service.py` líneas 27-31

**Problema:** Dos derivaciones diferentes de la misma `ENCRYPTION_KEY`:
- `auth_service.py`: `hashlib.sha256(key.encode()).digest()` — SHA-256 del string
- `usuario_service.py`: `bytes.fromhex(key_hex[:64])` — interpreta la key como hex

Producen claves de 32 bytes distintas. No es un bug funcional hoy (cifran campos distintos), pero es una trampa para quien mantenga o extienda el código.

**Solución:** Centralizar en una función en `core/security.py`:
```python
def derive_encryption_key(hex_key: str) -> bytes:
    return bytes.fromhex(hex_key[:64])
```
Y usarla en ambos servicios.

---

## Lo que se hace bien 👏

* **Aislamiento Multi-Tenant:** Excelente. `tenant_id` inyectado en todas las firmas de services/repositories. Se deriva del JWT, nunca del body/path.
* **Gestión de Secretos:** `config.py` valida longitudes mínimas de `SECRET_KEY` (64 chars) y `ENCRYPTION_KEY` (32 chars). Falla rápido en arranque.
* **Criptografía Fuerte:** Argon2id para passwords, AES-256-GCM para PII, SHA-256 para tokens opacos.
* **Rate Limiting:** `slowapi` con límites por ruta en todos los endpoints de autenticación.
* **RBAC Fail-Closed:** `require_permission` retorna 403 ante cualquier permiso faltante — sin excepciones silenciosas.
* **Soft Delete:** Todo usa `deleted_at` — nada se borra definitivamente. Auditoría append-only.
* **Refresh Token Rotation + Reuse Detection:** Familia de tokens con revocación en cascada si se detecta reutilización.
* **Audit Log en operaciones críticas:** Impersonación, asignación masiva, clonación y vacancia tienen entradas de audit log.
* **`extra='forbid'` en todos los schemas:** Rechaza campos no declarados en toda la API.

---

## Priorización de Correcciones

| # | Hallazgo | Severidad | Archivo | Esfuerzo |
|---|----------|-----------|---------|----------|
| 4 | IDOR `asignacion_masiva` — validar `usuario_ids` vs tenant | 🚨 ALTA | `equipo_service.py` | Bajo |
| 5 | Info leak en `reset-password` error message | 🔴 MEDIA-ALTA | `routers/auth.py` | Bajo |
| 7 | `_resolve_*_nombre` sin filtro de tenant | 🟡 MEDIA | `equipo_service.py` | Bajo |
| 8 | `buscar_usuarios` incluye inactivos | 🟡 MEDIA | `equipo_service.py` | Bajo |
| 6 | N+1 queries en `mis_asignaciones` | 🟡 MEDIA | `equipo_service.py` | Medio |
| 10 | Discrepancia derivación AES | 🟢 BAJA | `auth_service.py`, `usuario_service.py` | Bajo |
| 9 | `end_impersonation` sin revocación de token | 🟢 BAJA | `routers/auth.py` | Alto |

---

> **Nota del Arquitecto:** "Los hallazgos 4, 5, 7 y 8 tienen correcciones de bajo esfuerzo y alta prioridad. Hacelos en un mismo commit. El #6 (N+1) va en refactor separado. El #9 (revocación de JWT) es el único que requiere infraestructura nueva (Redis blocklist) — planificá para el sprint de hardening."
