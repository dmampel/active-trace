# Auditoría de Seguridad - Activia Trace (Backend)

## Resumen Ejecutivo

El backend de Activia Trace demuestra fundamentos sólidos (uso de Argon2, AES-256-GCM para datos sensibles, validación de tenants obligatoria en consultas). Sin embargo, se identificaron brechas críticas en **Control de Acceso (Impersonación)** y **Configuración de Red (CORS)** que deben ser corregidas antes de salir a producción.

---

## Hallazgos Críticos 🚨

### 1. Escalada de Privilegios vía Impersonación (Broken Access Control)
**Severidad: ALTA**
* **Problema:** En `auth_service.py` (`impersonate`), cualquier usuario que posea el permiso `impersonacion:usar` puede impersonar a **cualquier otro usuario** dentro de su tenant, incluyendo Super Administradores.
* **El código actual:** `target = await UserRepository.get_by_id(...)` verifica que el usuario objetivo exista y pertenezca al tenant, pero **no verifica si el nivel de privilegio del objetivo es superior al del usuario actual**.
* **Solución (Arquitectura):** Se debe implementar una jerarquía de roles (Role Hierarchy). Un usuario solo puede impersonar a usuarios con roles estrictamente iguales o inferiores al suyo. 

### 2. Ausencia Completa de CORS (Cross-Origin Resource Sharing)
**Severidad: MEDIA / ALTA (Afecta Disponibilidad y Seguridad)**
* **Problema:** En `main.py`, no se ha registrado `CORSMiddleware`. Si el frontend (Next.js, React, etc.) no corre bajo el mismo dominio exacto y puerto, los navegadores de los usuarios van a bloquear todas las peticiones (CORS policy error).
* **Solución:** Configurar `CORSMiddleware` limitando estrictamente el `allow_origins` a las URLs de producción del frontend. Nunca usar `["*"]` en producción con credenciales habilitadas.

---

## Puntos de Mejora 🛠

### 3. Fuerza de Contraseña (Password Strength) en Reset
**Severidad: MEDIA**
* **Problema:** En `auth_service.py` -> `reset_password`, se está hasheando `new_password` directamente sin pasar por una validación de complejidad.
* **Solución:** La validación suele estar en Pydantic (`schemas`), pero si llega una contraseña de 3 letras al servicio, el sistema la va a aceptar. Fomentá políticas fuertes (ej. mínimo 12 caracteres, alfanumérico) a nivel DTO/Schema.

---

## Lo que se hizo bien (Keep it up) 👏

* **Aislamiento Multi-Tenant:** Excelente. Se inyecta `tenant_id` en las firmas de todos los servicios y repositorios. No se deriva de la request (path/body) sino del token (`dependencies.py -> get_current_user`). Esto previene **Insecure Direct Object References (IDOR)** entre tenants.
* **Gestión de Secretos:** Muy bien implementado en `config.py` con validadores Pydantic que exigen 64 caracteres para `SECRET_KEY` y 32 para `ENCRYPTION_KEY`. Falla rápido si el entorno no es seguro.
* **Criptografía Fuerte:** Argon2 para hashes, AES-256-GCM para PII y SHA-256 para validación de tokens opacos.
* **Rate Limiting:** El uso de `slowapi` con decorators `@limiter.limit` en las rutas de autenticación mitiga eficazmente ataques de fuerza bruta.

---

> **Nota del Arquitecto:** "La seguridad no es un feature que se agrega al final, es la base sobre la que se construye. Corregí la impersonación urgente, porque es un agujero enorme por diseño."
