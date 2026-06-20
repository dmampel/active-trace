"""seed.py — Seed completo para testing de activia-trace.

Crea un dataset realista con:
- 1 tenant (UTN FRM)
- 7 usuarios (admin, coordinador, nexo, profesor, tutor, finanzas, alumno)
- Estructura académica: carrera, cohorte, 2 materias, instancias de dictado
- Asignaciones docentes (profesor, tutor) con contexto académico
- Padrón con 3 alumnos + calificaciones
- Comunicaciones (pendiente, enviada, cancelada)
- Encuentros: slot recurrente + único con instancias
- Guardia de tutor
- Evaluaciones (coloquio + parcial) con alumnos, reservas y resultados
- Fechas académicas
- Avisos (global, por materia, por rol)
- Tareas internas con comentarios
- Liquidaciones + factura
- Mensajería interna (hilo entre admin y coordinador)

Uso:
    cd backend
    python scripts/seed.py

Requiere .env con DATABASE_URL y ENCRYPTION_KEY válidos.
Las migraciones deben estar aplicadas (alembic upgrade head).
"""

import asyncio
import sys
import os
import uuid
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

from app.core.security import hash_password, AES256GCMCipher, derive_encryption_key


def _load_env(env_path: Path) -> dict[str, str]:
    """Lee el .env sin depender de pydantic-settings (evita validaciones estrictas)."""
    env: dict[str, str] = {}
    if not env_path.exists():
        return env
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        env[key.strip()] = val.strip().strip('"').strip("'")
    return env


# ── Helpers ────────────────────────────────────────────────────────────────────

def uid() -> uuid.UUID:
    return uuid.uuid4()


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


# ── Main ───────────────────────────────────────────────────────────────────────

async def seed():
    backend_dir = Path(__file__).parent.parent
    env = _load_env(backend_dir / ".env")

    # OS env takes precedence over .env file (allows overriding at runtime)
    database_url = os.environ.get("DATABASE_URL") or env.get("DATABASE_URL")
    encryption_key_raw = os.environ.get("ENCRYPTION_KEY") or env.get("ENCRYPTION_KEY", "")

    if not database_url:
        print("❌ DATABASE_URL no encontrado en .env ni en el entorno.")
        return
    if not encryption_key_raw:
        print("❌ ENCRYPTION_KEY no encontrado en .env ni en el entorno.")
        return

    # AES-256 necesita 32 bytes (64 hex chars).  Si la clave es texto plano corto,
    # la completamos con padding determinista para desarrollo local.
    if len(encryption_key_raw) < 64:
        encryption_key_raw = encryption_key_raw.encode().hex().ljust(64, "0")

    engine = create_async_engine(database_url, echo=False)
    Session = async_sessionmaker(engine, expire_on_commit=False)

    enc_key = derive_encryption_key(encryption_key_raw)
    cipher = AES256GCMCipher(enc_key)

    async with Session() as db:
        # ────────────────────────────────────────────────────────────────
        # 1. TENANT
        # ────────────────────────────────────────────────────────────────
        tenant_id = uid()
        await db.execute(
            text(
                "INSERT INTO tenant (id, name, is_active, requiere_aprobacion, created_at, updated_at) "
                "VALUES (:id, :name, true, false, now(), now()) "
                "ON CONFLICT (name) DO NOTHING"
            ),
            {"id": tenant_id, "name": "UTN FRM"},
        )
        row = await db.execute(text("SELECT id FROM tenant WHERE name = 'UTN FRM'"))
        tenant_id = row.scalar()
        print(f"✅ Tenant: UTN FRM ({tenant_id})")

        # ────────────────────────────────────────────────────────────────
        # 2. ROLES (resolución desde tabla — seeded por migraciones)
        # ────────────────────────────────────────────────────────────────
        rows = await db.execute(text("SELECT nombre, id FROM rol"))
        rol_map: dict[str, uuid.UUID] = {r[0]: r[1] for r in rows.fetchall()}
        if not rol_map:
            print("⚠️  No hay roles en DB. Ejecutá 'alembic upgrade head' primero.")
            return
        print(f"✅ Roles encontrados: {list(rol_map.keys())}")

        # ────────────────────────────────────────────────────────────────
        # 3. USUARIOS
        # ────────────────────────────────────────────────────────────────
        today = date.today()

        def make_user_insert(
            email: str,
            password: str = "trace1234",
            nombre: str = "",
            apellidos: str = "",
            legajo: str | None = None,
        ) -> tuple[uuid.UUID, dict]:
            uid_val = uid()
            return uid_val, {
                "id": uid_val,
                "tenant_id": tenant_id,
                "email": email,
                "password_hash": hash_password(password),
                "totp_enabled": False,
                "is_active": True,
                "nombre": nombre,
                "apellidos": apellidos,
                "legajo": legajo,
                "estado": "activa",
            }

        users: list[tuple[str, uuid.UUID, str, str | None]] = []  # (email, id, rol, legajo)

        user_specs = [
            ("admin@trace.utn.edu.ar",       "ADMIN",       "Ana",      "García",     "LEG-001"),
            ("coordinador@trace.utn.edu.ar",  "COORDINADOR", "Carlos",   "Mendoza",    "LEG-002"),
            ("nexo@trace.utn.edu.ar",         "NEXO",        "Natalia",  "Rojas",      "LEG-003"),
            ("profesor@trace.utn.edu.ar",     "PROFESOR",    "Pablo",    "Fernández",  "LEG-004"),
            ("tutor@trace.utn.edu.ar",        "TUTOR",       "Teresa",   "Vidal",      "LEG-005"),
            ("finanzas@trace.utn.edu.ar",     "FINANZAS",    "Felipe",   "Suárez",     "LEG-006"),
            ("alumno@trace.utn.edu.ar",       None,          "Lucía",    "Torres",     None),
        ]

        user_ids: dict[str, uuid.UUID] = {}
        for email, rol_nombre, nombre, apellidos, legajo in user_specs:
            user_id, params = make_user_insert(email, nombre=nombre, apellidos=apellidos, legajo=legajo)
            await db.execute(
                text(
                    "INSERT INTO \"user\" "
                    "(id, tenant_id, email, password_hash, totp_enabled, is_active, "
                    " nombre, apellidos, legajo, estado, created_at, updated_at) "
                    "VALUES (:id, :tenant_id, :email, :password_hash, :totp_enabled, :is_active, "
                    "        :nombre, :apellidos, :legajo, :estado, now(), now()) "
                    "ON CONFLICT (tenant_id, email) DO NOTHING"
                ),
                params,
            )
            row = await db.execute(
                text("SELECT id FROM \"user\" WHERE tenant_id = :tid AND email = :email"),
                {"tid": tenant_id, "email": email},
            )
            user_ids[email] = row.scalar()

            # user_rol (global role)
            if rol_nombre and rol_nombre in rol_map:
                await db.execute(
                    text(
                        "INSERT INTO user_rol (id, user_id, rol_id, tenant_id, desde, created_at, updated_at) "
                        "VALUES (:id, :user_id, :rol_id, :tenant_id, :desde, now(), now()) "
                        "ON CONFLICT DO NOTHING"
                    ),
                    {
                        "id": uid(),
                        "user_id": user_ids[email],
                        "rol_id": rol_map[rol_nombre],
                        "tenant_id": tenant_id,
                        "desde": today,
                    },
                )
        print(f"✅ Usuarios creados: {list(user_ids.keys())}")

        # Alias cortos
        u_admin = user_ids["admin@trace.utn.edu.ar"]
        u_coord = user_ids["coordinador@trace.utn.edu.ar"]
        u_nexo  = user_ids["nexo@trace.utn.edu.ar"]
        u_prof  = user_ids["profesor@trace.utn.edu.ar"]
        u_tutor = user_ids["tutor@trace.utn.edu.ar"]
        u_fin   = user_ids["finanzas@trace.utn.edu.ar"]
        u_alum  = user_ids["alumno@trace.utn.edu.ar"]

        # ────────────────────────────────────────────────────────────────
        # 4. ESTRUCTURA ACADÉMICA
        # ────────────────────────────────────────────────────────────────
        carrera_id = uid()
        await db.execute(
            text(
                "INSERT INTO carrera (id, tenant_id, codigo, nombre, estado, created_at, updated_at) "
                "VALUES (:id, :tid, :cod, :nom, 'activa', now(), now()) "
                "ON CONFLICT (tenant_id, codigo) DO NOTHING"
            ),
            {"id": carrera_id, "tid": tenant_id, "cod": "ISI", "nom": "Ingeniería en Sistemas"},
        )
        row = await db.execute(
            text("SELECT id FROM carrera WHERE tenant_id = :tid AND codigo = 'ISI'"),
            {"tid": tenant_id},
        )
        carrera_id = row.scalar()

        cohorte_id = uid()
        await db.execute(
            text(
                "INSERT INTO cohorte (id, tenant_id, carrera_id, nombre, anio, vig_desde, estado, created_at, updated_at) "
                "VALUES (:id, :tid, :cid, :nom, :anio, :desde, 'activa', now(), now()) "
                "ON CONFLICT (tenant_id, carrera_id, nombre) DO NOTHING"
            ),
            {
                "id": cohorte_id, "tid": tenant_id, "cid": carrera_id,
                "nom": "2024", "anio": 2024, "desde": date(2024, 3, 1),
            },
        )
        row = await db.execute(
            text("SELECT id FROM cohorte WHERE tenant_id = :tid AND nombre = '2024' AND carrera_id = :cid"),
            {"tid": tenant_id, "cid": carrera_id},
        )
        cohorte_id = row.scalar()

        materia_ids: dict[str, uuid.UUID] = {}
        for cod, nom in [("PROG1", "Programación I"), ("BD1", "Bases de Datos I")]:
            mid = uid()
            await db.execute(
                text(
                    "INSERT INTO materia (id, tenant_id, codigo, nombre, estado, created_at, updated_at) "
                    "VALUES (:id, :tid, :cod, :nom, 'activa', now(), now()) "
                    "ON CONFLICT (tenant_id, codigo) DO NOTHING"
                ),
                {"id": mid, "tid": tenant_id, "cod": cod, "nom": nom},
            )
            row = await db.execute(
                text("SELECT id FROM materia WHERE tenant_id = :tid AND codigo = :cod"),
                {"tid": tenant_id, "cod": cod},
            )
            materia_ids[cod] = row.scalar()

        m_prog = materia_ids["PROG1"]
        m_bd   = materia_ids["BD1"]

        # InstanciaDictado
        inst_ids: dict[str, uuid.UUID] = {}
        for cod, mid in [("PROG1", m_prog), ("BD1", m_bd)]:
            iid = uid()
            periodo = "2024-1C"
            await db.execute(
                text(
                    "INSERT INTO instancia_dictado "
                    "(id, tenant_id, materia_id, cohorte_id, nombre, periodo, estado, created_at, updated_at) "
                    "VALUES (:id, :tid, :mid, :coid, :nom, :per, 'activa', now(), now()) "
                    "ON CONFLICT (tenant_id, materia_id, cohorte_id, periodo) DO NOTHING"
                ),
                {
                    "id": iid, "tid": tenant_id, "mid": mid, "coid": cohorte_id,
                    "nom": f"{cod} 2024 1C", "per": periodo,
                },
            )
            row = await db.execute(
                text(
                    "SELECT id FROM instancia_dictado "
                    "WHERE tenant_id = :tid AND materia_id = :mid AND cohorte_id = :coid AND periodo = :per"
                ),
                {"tid": tenant_id, "mid": mid, "coid": cohorte_id, "per": periodo},
            )
            inst_ids[cod] = row.scalar()
        print(f"✅ Estructura académica: carrera={carrera_id}, cohorte={cohorte_id}, materias={list(materia_ids.keys())}")

        # ────────────────────────────────────────────────────────────────
        # 5. ASIGNACIONES CONTEXTUALES
        # ────────────────────────────────────────────────────────────────
        asig_ids: dict[str, uuid.UUID] = {}

        asig_specs = [
            # (key, usuario_id, rol, materia_id, carrera_id, cohorte_id, responsable_id)
            ("coord_global", u_coord, "COORDINADOR", None,   carrera_id, None,       None),
            ("nexo_global",  u_nexo,  "NEXO",        None,   carrera_id, cohorte_id, u_coord),
            ("prof_prog",    u_prof,  "PROFESOR",    m_prog, carrera_id, cohorte_id, u_coord),
            ("prof_bd",      u_prof,  "PROFESOR",    m_bd,   carrera_id, cohorte_id, u_coord),
            ("tutor_prog",   u_tutor, "TUTOR",       m_prog, carrera_id, cohorte_id, u_coord),
        ]

        for key, user_id, rol, mid, cid, coid, resp_id in asig_specs:
            aid = uid()
            await db.execute(
                text(
                    "INSERT INTO asignacion "
                    "(id, tenant_id, usuario_id, rol, materia_id, carrera_id, cohorte_id, "
                    " comisiones, responsable_id, desde, created_at, updated_at) "
                    "VALUES (:id, :tid, :uid, :rol, :mid, :cid, :coid, "
                    "        :com, :resp, :desde, now(), now()) "
                    "ON CONFLICT DO NOTHING"
                ),
                {
                    "id": aid, "tid": tenant_id, "uid": user_id, "rol": rol,
                    "mid": mid, "cid": cid, "coid": coid,
                    "com": "[]", "resp": resp_id, "desde": today,
                },
            )
            # Recuperar ID real (por si ya existía)
            q = (
                "SELECT id FROM asignacion WHERE tenant_id = :tid AND usuario_id = :uid "
                "AND rol = :rol"
            )
            params: dict = {"tid": tenant_id, "uid": user_id, "rol": rol}
            if mid:
                q += " AND materia_id = :mid"
                params["mid"] = mid
            else:
                q += " AND materia_id IS NULL"
            row = await db.execute(text(q + " LIMIT 1"), params)
            asig_ids[key] = row.scalar() or aid
        print(f"✅ Asignaciones: {list(asig_ids.keys())}")

        # ────────────────────────────────────────────────────────────────
        # 6. PADRÓN + CALIFICACIONES
        # ────────────────────────────────────────────────────────────────
        version_id = uid()
        await db.execute(
            text(
                "INSERT INTO version_padron "
                "(id, tenant_id, materia_id, cohorte_id, cargado_por, cargado_at, activa, created_at, updated_at) "
                "VALUES (:id, :tid, :mid, :coid, :por, now(), true, now(), now()) "
                "ON CONFLICT DO NOTHING"
            ),
            {"id": version_id, "tid": tenant_id, "mid": m_prog, "coid": cohorte_id, "por": u_prof},
        )
        row = await db.execute(
            text(
                "SELECT id FROM version_padron "
                "WHERE tenant_id = :tid AND materia_id = :mid AND cohorte_id = :coid AND activa = true"
            ),
            {"tid": tenant_id, "mid": m_prog, "coid": cohorte_id},
        )
        version_id = row.scalar()

        alumnos = [
            ("Lucía",     "Torres",   "lucia.torres@mail.com",   "A"),
            ("Marcos",    "Pérez",    "marcos.perez@mail.com",   "B"),
            ("Valentina", "Gómez",    "vale.gomez@mail.com",     "A"),
        ]
        entrada_ids: list[uuid.UUID] = []
        for nom, ape, email, comision in alumnos:
            eid = uid()
            await db.execute(
                text(
                    "INSERT INTO entrada_padron "
                    "(id, version_id, tenant_id, nombre, apellidos, email_enc, comision, created_at, updated_at) "
                    "VALUES (:id, :vid, :tid, :nom, :ape, :email, :com, now(), now()) "
                    "ON CONFLICT DO NOTHING"
                ),
                {
                    "id": eid, "vid": version_id, "tid": tenant_id,
                    "nom": nom, "ape": ape,
                    "email": cipher.encrypt(email),
                    "com": comision,
                },
            )
            row = await db.execute(
                text("SELECT id FROM entrada_padron WHERE version_id = :vid AND nombre = :nom AND apellidos = :ape"),
                {"vid": version_id, "nom": nom, "ape": ape},
            )
            entrada_ids.append(row.scalar())

        # Calificaciones para cada alumno
        notas = [8.5, 6.0, 9.0]
        for eid, nota in zip(entrada_ids, notas):
            await db.execute(
                text(
                    "INSERT INTO calificacion "
                    "(id, tenant_id, entrada_padron_id, materia_id, actividad, nota_numerica, origen, created_at, updated_at) "
                    "VALUES (:id, :tid, :eid, :mid, :act, :nota, 'Importado', now(), now()) "
                    "ON CONFLICT DO NOTHING"
                ),
                {"id": uid(), "tid": tenant_id, "eid": eid, "mid": m_prog, "act": "TP1", "nota": nota},
            )
        print(f"✅ Padrón: {len(entrada_ids)} alumnos con calificaciones")

        # ────────────────────────────────────────────────────────────────
        # 7. COMUNICACIONES
        # ────────────────────────────────────────────────────────────────
        com_specs = [
            ("Pendiente",  "Recordatorio TP1", "Recordá entregar el TP1 antes del viernes."),
            ("Enviado",    "Notas publicadas",  "Las notas del primer parcial ya están disponibles."),
            ("Cancelado",  "Prueba cancelada",  "Este mensaje fue cancelado antes de enviarse."),
        ]
        for estado, asunto, cuerpo in com_specs:
            enviado_at = now_utc() if estado == "Enviado" else None
            await db.execute(
                text(
                    "INSERT INTO comunicacion "
                    "(id, tenant_id, enviado_por, materia_id, destinatario, asunto, cuerpo, "
                    " estado, enviado_at, created_at, updated_at) "
                    "VALUES (:id, :tid, :por, :mid, :dest, :asunto, :cuerpo, "
                    "        :estado, :enviado_at, now(), now()) "
                    "ON CONFLICT DO NOTHING"
                ),
                {
                    "id": uid(), "tid": tenant_id, "por": u_prof, "mid": m_prog,
                    "dest": cipher.encrypt("grupo-comision-a@mail.com"),
                    "asunto": asunto, "cuerpo": cuerpo,
                    "estado": estado, "enviado_at": enviado_at,
                },
            )
        print("✅ Comunicaciones: 3 (pendiente, enviada, cancelada)")

        # ────────────────────────────────────────────────────────────────
        # 8. ENCUENTROS
        # ────────────────────────────────────────────────────────────────
        slot_rec_id = uid()
        await db.execute(
            text(
                "INSERT INTO slot_encuentro "
                "(id, tenant_id, asignacion_id, titulo, cant_semanas, fecha_inicio, dia_semana, hora, "
                " meet_url, descripcion, created_at, updated_at) "
                "VALUES (:id, :tid, :asig, :titulo, :sem, :fi, :dia, :hora, :url, :desc, now(), now()) "
                "ON CONFLICT DO NOTHING"
            ),
            {
                "id": slot_rec_id, "tid": tenant_id, "asig": asig_ids["prof_prog"],
                "titulo": "Clase semanal PROG1", "sem": 16,
                "fi": date(2024, 3, 4), "dia": "Lunes",
                "hora": time(18, 0), "url": "https://meet.google.com/abc-defg-hij",
                "desc": "Clase regular de Programación I",
            },
        )
        row = await db.execute(
            text("SELECT id FROM slot_encuentro WHERE tenant_id = :tid AND titulo = :t"),
            {"tid": tenant_id, "t": "Clase semanal PROG1"},
        )
        slot_rec_id = row.scalar()

        # Generar 3 instancias del slot recurrente
        for i in range(3):
            fecha = date(2024, 3, 4) + timedelta(weeks=i)
            await db.execute(
                text(
                    "INSERT INTO instancia_encuentro "
                    "(id, tenant_id, slot_id, fecha, hora, estado, meet_url, created_at, updated_at) "
                    "VALUES (:id, :tid, :slot, :fecha, :hora, :estado, :url, now(), now()) "
                    "ON CONFLICT DO NOTHING"
                ),
                {
                    "id": uid(), "tid": tenant_id, "slot": slot_rec_id,
                    "fecha": fecha, "hora": time(18, 0),
                    "estado": "Realizado" if i < 2 else "Programado",
                    "url": "https://meet.google.com/abc-defg-hij",
                },
            )
        print("✅ Encuentros: 1 slot recurrente + 3 instancias")

        # ────────────────────────────────────────────────────────────────
        # 9. GUARDIA DE TUTOR
        # ────────────────────────────────────────────────────────────────
        await db.execute(
            text(
                "INSERT INTO guardia "
                "(id, tenant_id, asignacion_id, materia_id, carrera_id, cohorte_id, "
                " dia, horario, estado, comentarios, created_at, updated_at) "
                "VALUES (:id, :tid, :asig, :mid, :cid, :coid, "
                "        :dia, :hor, 'Cubierta', :com, now(), now()) "
                "ON CONFLICT DO NOTHING"
            ),
            {
                "id": uid(), "tid": tenant_id, "asig": asig_ids["tutor_prog"],
                "mid": m_prog, "cid": carrera_id, "coid": cohorte_id,
                "dia": date(2024, 3, 5), "hor": "14:00–15:00",
                "com": "Alumnos con dudas sobre punteros en C.",
            },
        )
        print("✅ Guardia de tutor creada")

        # ────────────────────────────────────────────────────────────────
        # 10. EVALUACIONES + FECHAS ACADÉMICAS
        # ────────────────────────────────────────────────────────────────
        eval_id = uid()
        await db.execute(
            text(
                "INSERT INTO evaluacion "
                "(id, tenant_id, materia_id, cohorte_id, tipo, instancia, cupos_por_dia, created_at, updated_at) "
                "VALUES (:id, :tid, :mid, :coid, 'Coloquio', '1er Coloquio 2024', "
                "        :cupos, now(), now()) "
                "ON CONFLICT DO NOTHING"
            ),
            {
                "id": eval_id, "tid": tenant_id, "mid": m_prog, "coid": cohorte_id,
                "cupos": '{"2024-07-01": 10, "2024-07-02": 10}',
            },
        )
        row = await db.execute(
            text("SELECT id FROM evaluacion WHERE tenant_id = :tid AND instancia = '1er Coloquio 2024'"),
            {"tid": tenant_id},
        )
        eval_id = row.scalar()

        # Alumno habilitado
        await db.execute(
            text(
                "INSERT INTO evaluacion_alumno (evaluacion_id, alumno_id, tenant_id) "
                "VALUES (:eid, :aid, :tid) ON CONFLICT DO NOTHING"
            ),
            {"eid": eval_id, "aid": u_alum, "tid": tenant_id},
        )

        # Reserva
        await db.execute(
            text(
                "INSERT INTO reserva_evaluacion "
                "(id, tenant_id, evaluacion_id, alumno_id, fecha, estado, created_at, updated_at) "
                "VALUES (:id, :tid, :eid, :aid, '2024-07-01', 'activa', now(), now()) "
                "ON CONFLICT DO NOTHING"
            ),
            {"id": uid(), "tid": tenant_id, "eid": eval_id, "aid": u_alum},
        )

        # Resultado
        await db.execute(
            text(
                "INSERT INTO resultado_evaluacion "
                "(id, tenant_id, evaluacion_id, alumno_id, nota_final, created_at, updated_at) "
                "VALUES (:id, :tid, :eid, :aid, 'Aprobado', now(), now()) "
                "ON CONFLICT (evaluacion_id, alumno_id) DO NOTHING"
            ),
            {"id": uid(), "tid": tenant_id, "eid": eval_id, "aid": u_alum},
        )

        # Fecha académica
        await db.execute(
            text(
                "INSERT INTO fecha_academica "
                "(id, tenant_id, materia_id, cohorte_id, tipo, numero, periodo, fecha, titulo, created_at, updated_at) "
                "VALUES (:id, :tid, :mid, :coid, 'Parcial', 1, '2024-1C', '2024-05-10', "
                "        'Primer Parcial PROG1 2024', now(), now()) "
                "ON CONFLICT (tenant_id, materia_id, cohorte_id, tipo, numero, periodo) DO NOTHING"
            ),
            {"id": uid(), "tid": tenant_id, "mid": m_prog, "coid": cohorte_id},
        )
        print("✅ Evaluación + fecha académica + reserva + resultado creados")

        # ────────────────────────────────────────────────────────────────
        # 11. AVISOS
        # ────────────────────────────────────────────────────────────────
        aviso_specs = [
            {
                "alcance": "Global", "materia_id": None, "cohorte_id": None, "rol_destino": None,
                "severidad": "Info", "titulo": "Bienvenidos al ciclo 2024",
                "cuerpo": "Iniciamos el ciclo lectivo 2024. ¡Éxitos a todos!",
                "inicio_en": datetime(2024, 3, 1, 8, 0, tzinfo=timezone.utc),
                "requiere_ack": False,
            },
            {
                "alcance": "PorMateria", "materia_id": m_prog, "cohorte_id": None, "rol_destino": None,
                "severidad": "Advertencia", "titulo": "Entrega de TP1 — PROG1",
                "cuerpo": "Recordamos que la entrega del TP1 vence el viernes 22 de marzo a las 23:59.",
                "inicio_en": datetime(2024, 3, 18, 0, 0, tzinfo=timezone.utc),
                "requiere_ack": True,
            },
            {
                "alcance": "PorRol", "materia_id": None, "cohorte_id": None, "rol_destino": "TUTOR",
                "severidad": "Critico", "titulo": "Reunión de tutores — urgente",
                "cuerpo": "Se convoca a todos los tutores a la reunión del lunes 11 de marzo a las 18 hs.",
                "inicio_en": datetime(2024, 3, 9, 0, 0, tzinfo=timezone.utc),
                "requiere_ack": True,
            },
        ]
        for spec in aviso_specs:
            await db.execute(
                text(
                    "INSERT INTO aviso "
                    "(id, tenant_id, alcance, materia_id, cohorte_id, rol_destino, severidad, "
                    " titulo, cuerpo, inicio_en, orden, activo, requiere_ack, created_at, updated_at) "
                    "VALUES (:id, :tid, :alcance, :mid, :coid, :rol, :sev, "
                    "        :titulo, :cuerpo, :inicio_en, 0, true, :req_ack, now(), now()) "
                    "ON CONFLICT DO NOTHING"
                ),
                {
                    "id": uid(), "tid": tenant_id,
                    "alcance": spec["alcance"],
                    "mid": spec["materia_id"],
                    "coid": spec["cohorte_id"],
                    "rol": spec["rol_destino"],
                    "sev": spec["severidad"],
                    "titulo": spec["titulo"],
                    "cuerpo": spec["cuerpo"],
                    "inicio_en": spec["inicio_en"],
                    "req_ack": spec["requiere_ack"],
                },
            )
        print("✅ Avisos: 3 (global, por materia, por rol)")

        # ────────────────────────────────────────────────────────────────
        # 12. TAREAS INTERNAS
        # ────────────────────────────────────────────────────────────────
        tarea_id = uid()
        await db.execute(
            text(
                "INSERT INTO tarea "
                "(id, tenant_id, asignado_a, asignado_por, materia_id, estado, descripcion, created_at, updated_at) "
                "VALUES (:id, :tid, :a_a, :a_por, :mid, 'pendiente', :desc, now(), now()) "
                "ON CONFLICT DO NOTHING"
            ),
            {
                "id": tarea_id, "tid": tenant_id,
                "a_a": u_tutor, "a_por": u_coord, "mid": m_prog,
                "desc": "Revisar asistencia de la comisión A semana del 18/03.",
            },
        )
        row = await db.execute(
            text("SELECT id FROM tarea WHERE tenant_id = :tid AND asignado_a = :uid LIMIT 1"),
            {"tid": tenant_id, "uid": u_tutor},
        )
        tarea_id = row.scalar()

        await db.execute(
            text(
                "INSERT INTO comentario_tarea "
                "(id, tenant_id, tarea_id, autor_id, texto, creado_at) "
                "VALUES (:id, :tid, :tarea, :autor, :texto, now()) "
                "ON CONFLICT DO NOTHING"
            ),
            {
                "id": uid(), "tid": tenant_id, "tarea": tarea_id,
                "autor": u_coord, "texto": "Por favor terminarlo antes del viernes.",
            },
        )

        # Segunda tarea — en progreso
        tarea2_id = uid()
        await db.execute(
            text(
                "INSERT INTO tarea "
                "(id, tenant_id, asignado_a, asignado_por, estado, descripcion, created_at, updated_at) "
                "VALUES (:id, :tid, :a_a, :a_por, 'en_progreso', :desc, now(), now()) "
                "ON CONFLICT DO NOTHING"
            ),
            {
                "id": tarea2_id, "tid": tenant_id,
                "a_a": u_prof, "a_por": u_coord,
                "desc": "Actualizar el programa de la materia PROG1 para el cuatrimestre.",
            },
        )
        print("✅ Tareas internas: 2 (pendiente, en progreso) con comentario")

        # ────────────────────────────────────────────────────────────────
        # 13. LIQUIDACIONES + FACTURA
        # ────────────────────────────────────────────────────────────────
        # SalarioBase para TUTOR y PROFESOR
        for rol_nom, monto in [("TUTOR", 150000), ("PROFESOR", 200000)]:
            await db.execute(
                text(
                    "INSERT INTO salario_base "
                    "(id, tenant_id, rol, monto, desde, created_at, updated_at) "
                    "VALUES (:id, :tid, :rol, :monto, :desde, now(), now()) "
                    "ON CONFLICT DO NOTHING"
                ),
                {"id": uid(), "tid": tenant_id, "rol": rol_nom, "monto": monto, "desde": date(2024, 1, 1)},
            )

        # Liquidación del PROFESOR
        await db.execute(
            text(
                "INSERT INTO liquidacion "
                "(id, tenant_id, cohorte_id, periodo, usuario_id, rol, comisiones, "
                " monto_base, monto_plus, total, es_nexo, excluido_por_factura, estado, created_at, updated_at) "
                "VALUES (:id, :tid, :coid, :per, :uid, 'PROFESOR', '[]', "
                "        200000, 0, 200000, false, false, 'Abierta', now(), now()) "
                "ON CONFLICT (tenant_id, cohorte_id, periodo, usuario_id) DO NOTHING"
            ),
            {
                "id": uid(), "tid": tenant_id, "coid": cohorte_id,
                "per": "2024-1C", "uid": u_prof,
            },
        )

        # Liquidación cerrada del TUTOR
        await db.execute(
            text(
                "INSERT INTO liquidacion "
                "(id, tenant_id, cohorte_id, periodo, usuario_id, rol, comisiones, "
                " monto_base, monto_plus, total, es_nexo, excluido_por_factura, estado, created_at, updated_at) "
                "VALUES (:id, :tid, :coid, :per, :uid, 'TUTOR', '[]', "
                "        150000, 10000, 160000, false, false, 'Cerrada', now(), now()) "
                "ON CONFLICT (tenant_id, cohorte_id, periodo, usuario_id) DO NOTHING"
            ),
            {
                "id": uid(), "tid": tenant_id, "coid": cohorte_id,
                "per": "2024-1C", "uid": u_tutor,
            },
        )

        # Factura del profesor (facturante)
        await db.execute(
            text(
                "INSERT INTO factura "
                "(id, tenant_id, usuario_id, periodo, detalle, estado, cargada_at, created_at, updated_at) "
                "VALUES (:id, :tid, :uid, '2024-1C', 'Factura B 0001-00000123', 'Pendiente', now(), now(), now()) "
                "ON CONFLICT DO NOTHING"
            ),
            {"id": uid(), "tid": tenant_id, "uid": u_prof},
        )
        print("✅ Liquidaciones: 2 (abierta, cerrada) + 1 factura")

        # ────────────────────────────────────────────────────────────────
        # 14. MENSAJERÍA INTERNA
        # ────────────────────────────────────────────────────────────────
        hilo_id = uid()
        await db.execute(
            text(
                "INSERT INTO hilo_mensaje "
                "(id, tenant_id, asunto, creado_por, created_at, updated_at) "
                "VALUES (:id, :tid, :asunto, :por, now(), now()) "
                "ON CONFLICT DO NOTHING"
            ),
            {"id": hilo_id, "tid": tenant_id, "asunto": "Consulta sobre calificaciones", "por": u_coord},
        )
        row = await db.execute(
            text("SELECT id FROM hilo_mensaje WHERE tenant_id = :tid AND creado_por = :por LIMIT 1"),
            {"tid": tenant_id, "por": u_coord},
        )
        hilo_id = row.scalar()

        mensajes = [
            (u_coord, u_admin, "Hola, ¿podés revisar las calificaciones de PROG1? Hay una nota que no coincide."),
            (u_admin, u_coord, "Ya lo verifico y te aviso a la brevedad."),
        ]
        for autor, dest, cuerpo in mensajes:
            await db.execute(
                text(
                    "INSERT INTO mensaje_interno "
                    "(id, tenant_id, hilo_id, autor_id, destinatario_id, cuerpo, leido, created_at, updated_at) "
                    "VALUES (:id, :tid, :hilo, :autor, :dest, :cuerpo, :leido, now(), now()) "
                    "ON CONFLICT DO NOTHING"
                ),
                {
                    "id": uid(), "tid": tenant_id, "hilo": hilo_id,
                    "autor": autor, "dest": dest, "cuerpo": cuerpo,
                    "leido": autor == u_coord,  # primer mensaje ya leído
                },
            )
        print("✅ Mensajería: 1 hilo con 2 mensajes")

        # ────────────────────────────────────────────────────────────────
        # COMMIT
        # ────────────────────────────────────────────────────────────────
        await db.commit()

    print()
    print("═" * 60)
    print("🎉  Seed completado exitosamente")
    print("═" * 60)
    print()
    print("CREDENCIALES DE ACCESO (password: trace1234)")
    print("─" * 60)
    rows_spec = [
        ("ADMIN",       "admin@trace.utn.edu.ar"),
        ("COORDINADOR", "coordinador@trace.utn.edu.ar"),
        ("NEXO",        "nexo@trace.utn.edu.ar"),
        ("PROFESOR",    "profesor@trace.utn.edu.ar"),
        ("TUTOR",       "tutor@trace.utn.edu.ar"),
        ("FINANZAS",    "finanzas@trace.utn.edu.ar"),
        ("(alumno)",    "alumno@trace.utn.edu.ar"),
    ]
    for rol_nom, email in rows_spec:
        print(f"  {rol_nom:<14} {email}")
    print()
    print("TENANT: UTN FRM")
    print("CARRERA: Ingeniería en Sistemas (ISI)")
    print("MATERIAS: Programación I (PROG1), Bases de Datos I (BD1)")
    print("COHORTE: 2024 | PERÍODO: 2024-1C")


if __name__ == "__main__":
    asyncio.run(seed())
