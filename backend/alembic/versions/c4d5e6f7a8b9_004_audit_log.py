"""004_audit_log

Revision ID: c4d5e6f7a8b9
Revises: a1b2c3d4e5f6
Create Date: 2026-06-07 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "c4d5e6f7a8b9"
down_revision: Union[str, None] = "a1b2c3d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "audit_log",
        sa.Column("id", sa.UUID(), nullable=False, default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column("fecha_hora", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("actor_id", sa.UUID(), nullable=False),
        sa.Column("impersonado_id", sa.UUID(), nullable=True),
        sa.Column("materia_id", sa.UUID(), nullable=True),
        sa.Column("accion", sa.Text(), nullable=False),
        sa.Column("detalle", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("filas_afectadas", sa.Integer(), nullable=True),
        sa.Column("ip", sa.Text(), nullable=True),
        sa.Column("user_agent", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenant.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["actor_id"], ["user.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["impersonado_id"], ["user.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_audit_log_tenant_fecha", "audit_log", ["tenant_id", "fecha_hora"])
    op.create_index("ix_audit_log_actor", "audit_log", ["actor_id"])

    op.execute("""
        CREATE OR REPLACE FUNCTION audit_log_immutable()
        RETURNS TRIGGER AS $$
        BEGIN
            RAISE EXCEPTION 'audit_log is append-only: UPDATE and DELETE are not permitted';
        END;
        $$ LANGUAGE plpgsql;
    """)

    op.execute("""
        CREATE TRIGGER audit_log_no_update_delete
        BEFORE UPDATE OR DELETE ON audit_log
        FOR EACH ROW EXECUTE FUNCTION audit_log_immutable();
    """)


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS audit_log_no_update_delete ON audit_log;")
    op.execute("DROP FUNCTION IF EXISTS audit_log_immutable;")
    op.drop_index("ix_audit_log_actor", table_name="audit_log")
    op.drop_index("ix_audit_log_tenant_fecha", table_name="audit_log")
    op.drop_table("audit_log")
