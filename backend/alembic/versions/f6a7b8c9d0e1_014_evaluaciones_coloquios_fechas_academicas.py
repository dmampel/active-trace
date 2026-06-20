"""014_evaluaciones_coloquios_fechas_academicas

Revision ID: f6a7b8c9d0e1
Revises: e5f6a7b8c9d0
Create Date: 2026-06-18 00:00:00.000000

Crea las tablas del módulo de coloquios/evaluaciones (C-14):
- Enums: `tipoevaluacion`, `estadoreserva`, `tipofechaacademica`
- Tabla `evaluacion`: convocatoria con cupos_por_dia JSONB y soft delete
- Tabla `evaluacion_alumno`: alumnos habilitados a una convocatoria
- Tabla `reserva_evaluacion`: turno reservado por ALUMNO
- Tabla `resultado_evaluacion`: nota final por (evaluacion, alumno)
- Tabla `fecha_academica`: calendarización informativa con soft delete
- Permisos: coloquios:gestionar, coloquios:ver, coloquios:reservar,
           fechas_academicas:gestionar, fechas_academicas:ver
- Asignación de permisos a roles según D4
"""

from typing import Sequence, Union
import uuid
from datetime import datetime, timezone

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision: str = "f6a7b8c9d0e1"
down_revision: Union[str, None] = "e5f6a7b8c9d0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── 2. Tabla evaluacion ───────────────────────────────────────────────────
    op.create_table(
        "evaluacion",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column(
            "tenant_id",
            UUID(as_uuid=True),
            sa.ForeignKey("tenant.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "materia_id",
            UUID(as_uuid=True),
            sa.ForeignKey("materia.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "cohorte_id",
            UUID(as_uuid=True),
            sa.ForeignKey("cohorte.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "tipo",
            sa.Enum(
                "Coloquio", "Parcial", "Recuperatorio", "TP",
                name="tipoevaluacion",
            ),
            nullable=False,
        ),
        sa.Column("instancia", sa.String(255), nullable=False),
        sa.Column("cupos_por_dia", JSONB, nullable=False, server_default="{}"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_evaluacion_tenant_id", "evaluacion", ["tenant_id"])
    op.create_index("ix_evaluacion_materia_id", "evaluacion", ["materia_id"])
    op.create_index("ix_evaluacion_cohorte_id", "evaluacion", ["cohorte_id"])
    op.create_index("ix_evaluacion_materia_cohorte", "evaluacion", ["materia_id", "cohorte_id"])

    # ── 3. Tabla evaluacion_alumno ────────────────────────────────────────────
    op.create_table(
        "evaluacion_alumno",
        sa.Column(
            "evaluacion_id",
            UUID(as_uuid=True),
            sa.ForeignKey("evaluacion.id", ondelete="CASCADE"),
            primary_key=True,
            nullable=False,
        ),
        sa.Column(
            "alumno_id",
            UUID(as_uuid=True),
            sa.ForeignKey("user.id", ondelete="CASCADE"),
            primary_key=True,
            nullable=False,
        ),
        sa.Column(
            "tenant_id",
            UUID(as_uuid=True),
            sa.ForeignKey("tenant.id", ondelete="CASCADE"),
            nullable=False,
        ),
    )
    op.create_index("ix_evaluacion_alumno_evaluacion", "evaluacion_alumno", ["evaluacion_id"])
    op.create_index("ix_evaluacion_alumno_alumno", "evaluacion_alumno", ["alumno_id"])
    op.create_index("ix_evaluacion_alumno_tenant", "evaluacion_alumno", ["tenant_id"])

    # ── 4. Tabla reserva_evaluacion ───────────────────────────────────────────
    op.create_table(
        "reserva_evaluacion",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column(
            "tenant_id",
            UUID(as_uuid=True),
            sa.ForeignKey("tenant.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "evaluacion_id",
            UUID(as_uuid=True),
            sa.ForeignKey("evaluacion.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "alumno_id",
            UUID(as_uuid=True),
            sa.ForeignKey("user.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("fecha", sa.String(10), nullable=False),  # ISO date YYYY-MM-DD
        sa.Column(
            "estado",
            sa.Enum(
                "Activa", "Cancelada",
                name="estadoreserva",
            ),
            nullable=False,
            server_default="activa",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index("ix_reserva_evaluacion_tenant", "reserva_evaluacion", ["tenant_id"])
    op.create_index("ix_reserva_evaluacion_evaluacion", "reserva_evaluacion", ["evaluacion_id"])
    op.create_index("ix_reserva_evaluacion_alumno", "reserva_evaluacion", ["alumno_id"])

    # ── 5. Tabla resultado_evaluacion ─────────────────────────────────────────
    op.create_table(
        "resultado_evaluacion",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column(
            "tenant_id",
            UUID(as_uuid=True),
            sa.ForeignKey("tenant.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "evaluacion_id",
            UUID(as_uuid=True),
            sa.ForeignKey("evaluacion.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "alumno_id",
            UUID(as_uuid=True),
            sa.ForeignKey("user.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("nota_final", sa.Text, nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.UniqueConstraint("evaluacion_id", "alumno_id", name="uq_resultado_evaluacion_alumno"),
    )
    op.create_index("ix_resultado_evaluacion_tenant", "resultado_evaluacion", ["tenant_id"])
    op.create_index("ix_resultado_evaluacion_evaluacion", "resultado_evaluacion", ["evaluacion_id"])

    # ── 6. Tabla fecha_academica ──────────────────────────────────────────────
    op.create_table(
        "fecha_academica",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column(
            "tenant_id",
            UUID(as_uuid=True),
            sa.ForeignKey("tenant.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "materia_id",
            UUID(as_uuid=True),
            sa.ForeignKey("materia.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "cohorte_id",
            UUID(as_uuid=True),
            sa.ForeignKey("cohorte.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "tipo",
            sa.Enum(
                "Parcial", "TP", "Coloquio", "Recuperatorio",
                name="tipofechaacademica",
            ),
            nullable=False,
        ),
        sa.Column("numero", sa.Integer, nullable=False),
        sa.Column("periodo", sa.String(50), nullable=False),
        sa.Column("fecha", sa.String(10), nullable=False),  # ISO date YYYY-MM-DD
        sa.Column("titulo", sa.String(255), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_fecha_academica_tenant", "fecha_academica", ["tenant_id"])
    op.create_index("ix_fecha_academica_materia_id", "fecha_academica", ["materia_id"])
    op.create_index("ix_fecha_academica_cohorte_id", "fecha_academica", ["cohorte_id"])
    op.create_index(
        "ix_fecha_academica_materia_cohorte", "fecha_academica", ["materia_id", "cohorte_id"]
    )

    # ── 7. Permisos y asignación a roles (D4) ─────────────────────────────────
    connection = op.get_bind()
    now = datetime.now(timezone.utc)

    permisos = [
        ("coloquios:gestionar", "Crear y editar convocatorias de coloquio"),
        ("coloquios:ver", "Ver convocatorias y métricas de coloquios"),
        ("coloquios:reservar", "Reservar turno de coloquio (ALUMNO)"),
        ("fechas_academicas:gestionar", "Crear y editar fechas académicas"),
        ("fechas_academicas:ver", "Ver fechas académicas del tenant"),
    ]
    permiso_ids: dict[str, uuid.UUID] = {}
    for nombre, descripcion in permisos:
        pid = uuid.uuid4()
        permiso_ids[nombre] = pid
        connection.execute(
            sa.text(
                "INSERT INTO permiso (id, nombre, descripcion, created_at, updated_at) "
                "VALUES (:id, :nombre, :descripcion, :created_at, :updated_at)"
            ),
            {
                "id": pid,
                "nombre": nombre,
                "descripcion": descripcion,
                "created_at": now,
                "updated_at": now,
            },
        )

    # D4: asignación de permisos a roles
    # coloquios:gestionar     → COORDINADOR, ADMIN
    # coloquios:ver           → COORDINADOR, ADMIN, PROFESOR
    # coloquios:reservar      → ALUMNO
    # fechas_academicas:gestionar → COORDINADOR, ADMIN, PROFESOR
    # fechas_academicas:ver   → todos los roles
    todos_los_roles = ["ALUMNO", "TUTOR", "PROFESOR", "COORDINADOR", "NEXO", "ADMIN", "FINANZAS"]
    asignaciones = [
        ("coloquios:gestionar", ["COORDINADOR", "ADMIN"]),
        ("coloquios:ver", ["COORDINADOR", "ADMIN", "PROFESOR"]),
        ("coloquios:reservar", ["ALUMNO"]),
        ("fechas_academicas:gestionar", ["COORDINADOR", "ADMIN", "PROFESOR"]),
        ("fechas_academicas:ver", todos_los_roles),
    ]
    for perm_nombre, roles in asignaciones:
        pid = permiso_ids[perm_nombre]
        for rol_nombre in roles:
            rol_row = connection.execute(
                sa.text("SELECT id FROM rol WHERE nombre = :nombre"),
                {"nombre": rol_nombre},
            ).fetchone()
            if rol_row is None:
                continue
            connection.execute(
                sa.text(
                    "INSERT INTO rol_permiso (id, rol_id, permiso_id, created_at, updated_at) "
                    "VALUES (:id, :rol_id, :permiso_id, :created_at, :updated_at)"
                ),
                {
                    "id": uuid.uuid4(),
                    "rol_id": rol_row[0],
                    "permiso_id": pid,
                    "created_at": now,
                    "updated_at": now,
                },
            )


def downgrade() -> None:
    connection = op.get_bind()

    # Eliminar permisos coloquios:* y fechas_academicas:*
    connection.execute(
        sa.text(
            "DELETE FROM permiso WHERE nombre LIKE 'coloquios:%' "
            "OR nombre LIKE 'fechas_academicas:%'"
        )
    )

    # Eliminar tablas en orden inverso (sin dependencias colgantes)
    op.drop_index("ix_fecha_academica_materia_cohorte", table_name="fecha_academica")
    op.drop_index("ix_fecha_academica_cohorte_id", table_name="fecha_academica")
    op.drop_index("ix_fecha_academica_materia_id", table_name="fecha_academica")
    op.drop_index("ix_fecha_academica_tenant", table_name="fecha_academica")
    op.drop_table("fecha_academica")

    op.drop_index("ix_resultado_evaluacion_evaluacion", table_name="resultado_evaluacion")
    op.drop_index("ix_resultado_evaluacion_tenant", table_name="resultado_evaluacion")
    op.drop_table("resultado_evaluacion")

    op.drop_index("ix_reserva_evaluacion_alumno", table_name="reserva_evaluacion")
    op.drop_index("ix_reserva_evaluacion_evaluacion", table_name="reserva_evaluacion")
    op.drop_index("ix_reserva_evaluacion_tenant", table_name="reserva_evaluacion")
    op.drop_table("reserva_evaluacion")

    op.drop_index("ix_evaluacion_alumno_tenant", table_name="evaluacion_alumno")
    op.drop_index("ix_evaluacion_alumno_alumno", table_name="evaluacion_alumno")
    op.drop_index("ix_evaluacion_alumno_evaluacion", table_name="evaluacion_alumno")
    op.drop_table("evaluacion_alumno")

    op.drop_index("ix_evaluacion_materia_cohorte", table_name="evaluacion")
    op.drop_index("ix_evaluacion_cohorte_id", table_name="evaluacion")
    op.drop_index("ix_evaluacion_materia_id", table_name="evaluacion")
    op.drop_index("ix_evaluacion_tenant_id", table_name="evaluacion")
    op.drop_table("evaluacion")

    # Eliminar enums
    op.execute("DROP TYPE IF EXISTS tipofechaacademica")
    op.execute("DROP TYPE IF EXISTS estadoreserva")
    op.execute("DROP TYPE IF EXISTS tipoevaluacion")
