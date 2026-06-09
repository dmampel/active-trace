"""Tests de schemas de usuarios — Strict TDD.

Task 4.2: schema rechaza campo no declarado (422 / ValidationError).
Task 4.4: UsuarioListItem NO incluye dni/cuil/cbu/alias_cbu;
          UsuarioDetail SÍ incluye PII descifrada.
"""
import pytest
from pydantic import ValidationError


# ── 4.2 Schema rechaza campo no declarado ─────────────────────────────────────

def test_usuario_create_rejects_undeclared_field():
    from app.schemas.usuario import UsuarioCreate
    with pytest.raises(ValidationError) as exc_info:
        UsuarioCreate(
            email="test@example.com",
            password="secret",
            campo_fantasma="valor_no_declarado",  # campo extra → debe rechazar
        )
    errors = exc_info.value.errors()
    assert any(e["type"] == "extra_forbidden" for e in errors)


def test_usuario_update_rejects_undeclared_field():
    from app.schemas.usuario import UsuarioUpdate
    with pytest.raises(ValidationError) as exc_info:
        UsuarioUpdate(nombre="Juan", campo_extra="no_permitido")
    errors = exc_info.value.errors()
    assert any(e["type"] == "extra_forbidden" for e in errors)


def test_usuario_list_item_rejects_undeclared_field():
    """UsuarioListItem también rechaza campos no declarados."""
    import uuid
    from app.schemas.usuario import UsuarioListItem
    from app.models.estructura import EstadoEntidad
    with pytest.raises(ValidationError) as exc_info:
        UsuarioListItem(
            id=uuid.uuid4(),
            tenant_id=uuid.uuid4(),
            email="a@b.com",
            facturador=False,
            estado=EstadoEntidad.activa,
            campo_extra="no_permitido",
        )
    errors = exc_info.value.errors()
    assert any(e["type"] == "extra_forbidden" for e in errors)


# ── 4.4 DTO listado sin PII; DTO detalle con PII ──────────────────────────────

def test_usuario_list_item_does_not_include_pii():
    """UsuarioListItem no tiene los campos dni/cuil/cbu/alias_cbu."""
    import uuid
    from app.schemas.usuario import UsuarioListItem
    from app.models.estructura import EstadoEntidad
    item = UsuarioListItem(
        id=uuid.uuid4(),
        tenant_id=uuid.uuid4(),
        email="test@example.com",
        facturador=False,
        estado=EstadoEntidad.activa,
    )
    data = item.model_dump()
    # PII fields must NOT be present
    for pii_field in ("dni", "cuil", "cbu", "alias_cbu"):
        assert pii_field not in data, f"UsuarioListItem no debe exponer campo PII: {pii_field}"


def test_usuario_detail_includes_pii_fields():
    """UsuarioDetail incluye dni/cuil/cbu/alias_cbu (descifrados)."""
    import uuid
    from app.schemas.usuario import UsuarioDetail
    from app.models.estructura import EstadoEntidad
    detail = UsuarioDetail(
        id=uuid.uuid4(),
        tenant_id=uuid.uuid4(),
        email="test@example.com",
        facturador=False,
        estado=EstadoEntidad.activa,
        dni="12345678",
        cuil="20-12345678-9",
        cbu="0000000000000000000000",
        alias_cbu="mi.alias",
    )
    data = detail.model_dump()
    assert data["dni"] == "12345678"
    assert data["cuil"] == "20-12345678-9"
    assert data["cbu"] == "0000000000000000000000"
    assert data["alias_cbu"] == "mi.alias"


def test_usuario_detail_pii_optional_can_be_none():
    """PII en UsuarioDetail puede ser None si el usuario no tiene esos datos."""
    import uuid
    from app.schemas.usuario import UsuarioDetail
    from app.models.estructura import EstadoEntidad
    detail = UsuarioDetail(
        id=uuid.uuid4(),
        tenant_id=uuid.uuid4(),
        email="test@example.com",
        facturador=False,
        estado=EstadoEntidad.activa,
    )
    data = detail.model_dump()
    assert data["dni"] is None
    assert data["cuil"] is None
    assert data["cbu"] is None
    assert data["alias_cbu"] is None
