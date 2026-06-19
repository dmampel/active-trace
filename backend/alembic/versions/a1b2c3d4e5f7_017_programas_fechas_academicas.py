"""017_programas_fechas_academicas

Revision ID: a1b2c3d4e5f7
Revises: c16d3e4f5a6b
Create Date: 2026-06-18 00:00:00.000000

Crea las tablas del módulo de programas y fechas académicas (C-17):
- Tabla `programa_materia`: syllabus vinculado a (materia, carrera, cohorte)
  con UniqueConstraint por contexto académico.
- UniqueConstraint en `fecha_academica`: (tenant_id, materia_id, cohorte_id,
  tipo, numero, periodo) — una fecha por instancia evaluativa.
- Índice compuesto en `fecha_academica` por (tenant_id, materia_id, cohorte_id, periodo).
- Permisos: `estructura:gestionar` y `estructura:leer` (idempotente).
"""

from typing import Sequence, Union
import uuid
from datetime import datetime, timezone

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision: str = "a1b2c3d4e5f7"
down_revision: Union[str, None] = "c16d3e4f5a6b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── 1. Tabla programa_materia ─────────────────────────────────────────────
    op.create_table(
        "programa_materia",
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
            "carrera_id",
            UUID(as_uuid=True),
            sa.ForeignKey("carrera.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "cohorte_id",
            UUID(as_uuid=True),
            sa.ForeignKey("cohorte.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("titulo", sa.String(255), nullable=False),
        sa.Column("referencia_archivo", sa.Text, nullable=True),
        sa.Column("cargado_at", sa.DateTime(timezone=True), nullable=True),
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
        sa.UniqueConstraint(
            "tenant_id", "materia_id", "carrera_id", "cohorte_id",
            name="uq_programa_materia_contexto",
        ),
    )
    op.create_index("ix_programa_materia_tenant_id", "programa_materia", ["tenant_id"])
    op.create_index("ix_programa_materia_materia_id", "programa_materia", ["materia_id"])
    op.create_index("ix_programa_materia_carrera_id", "programa_materia", ["carrera_id"])
    op.create_index("ix_programa_materia_cohorte_id", "programa_materia", ["cohorte_id"])
    op.create_index(
        "ix_programa_materia_tenant_materia_carrera_cohorte",
        "programa_materia",
        ["tenant_id", "materia_id", "carrera_id", "cohorte_id"],
    )

    # ── 2. UniqueConstraint y nuevo índice en fecha_academica ─────────────────
    # La tabla ya existe (creada en C-14 migration 014).
    # Agregamos el constraint de unicidad y el índice por periodo.
    op.create_unique_constraint(
        "uq_fecha_academica_contexto",
        "fecha_academica",
        ["tenant_id", "materia_id", "cohorte_id", "tipo", "numero", "periodo"],
    )
    op.create_index(
        "ix_fecha_academica_materia_cohorte_periodo",
        "fecha_academica",
        ["tenant_id", "materia_id", "cohorte_id", "periodo"],
    )

    # ── 3. Permisos estructura:gestionar y estructura:leer (idempotente) ──────
    connection = op.get_bind()
    now = datetime.now(timezone.utc)

    permisos = [
        ("estructura:gestionar", "Crear y editar programas y fechas académicas"),
        ("estructura:leer", "Ver programas y fechas académicas del tenant"),
    ]

    permiso_ids: dict[str, uuid.UUID] = {}
    for nombre, descripcion in permisos:
        existing = connection.execute(
            sa.text("SELECT id FROM permiso WHERE nombre = :nombre"),
            {"nombre": nombre},
        ).fetchone()

        if existing is None:
            pid = uuid.uuid4()
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
            permiso_ids[nombre] = pid
        else:
            permiso_ids[nombre] = existing[0]

    # estructura:gestionar → COORDINADOR, ADMIN
    # estructura:leer      → TUTOR, PROFESOR, COORDINADOR, ADMIN
    asignaciones = [
        ("estructura:gestionar", ["COORDINADOR", "ADMIN"]),
        ("estructura:leer", ["TUTOR", "PROFESOR", "COORDINADOR", "ADMIN"]),
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
            existing_rp = connection.execute(
                sa.text(
                    "SELECT id FROM rol_permiso "
                    "WHERE rol_id = :rol_id AND permiso_id = :permiso_id"
                ),
                {"rol_id": rol_row[0], "permiso_id": pid},
            ).fetchone()
            if existing_rp is None:
                connection.execute(
                    sa.text(
                        "INSERT INTO rol_permiso "
                        "(id, rol_id, permiso_id, created_at, updated_at) "
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

    # Eliminar permisos estructura:* (cascade elimina rol_permiso)
    connection.execute(
        sa.text("DELETE FROM permiso WHERE nombre IN ('estructura:gestionar', 'estructura:leer')")
    )

    # Eliminar índice y constraint de fecha_academica
    op.drop_index("ix_fecha_academica_materia_cohorte_periodo", table_name="fecha_academica")
    op.drop_constraint("uq_fecha_academica_contexto", "fecha_academica", type_="unique")

    # Eliminar índices y tabla programa_materia
    op.drop_index(
        "ix_programa_materia_tenant_materia_carrera_cohorte",
        table_name="programa_materia",
    )
    op.drop_index("ix_programa_materia_cohorte_id", table_name="programa_materia")
    op.drop_index("ix_programa_materia_carrera_id", table_name="programa_materia")
    op.drop_index("ix_programa_materia_materia_id", table_name="programa_materia")
    op.drop_index("ix_programa_materia_tenant_id", table_name="programa_materia")
    op.drop_table("programa_materia")
