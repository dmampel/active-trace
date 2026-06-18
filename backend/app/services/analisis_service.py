"""Servicio de análisis de atrasados (C-11).

Responsabilidades:
- Orquesta repository + dominio puro.
- Resuelve el scope (PROFESOR → asignacion_id; COORD/ADMIN → materia completa).
- Descifra emails usando AES-256 antes de pasar a dominio.
- Sin acceso directo a DB (siempre vía repositorios).
- Sin lógica de negocio: eso es dominio/atrasados.py.

Identidad: SIEMPRE desde CurrentUser del JWT. Nunca de URL/body.
"""

from __future__ import annotations

import csv
import io
import uuid
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import record_audit, ANALISIS_ATRASADOS_VER
from app.core.dependencies import CurrentUser
from app.core.security import AES256GCMCipher, derive_encryption_key
from app.core.config import Settings
from app.domain.atrasados import (
    AlumnoCalificacionesDTO,
    FinalizacionDTO,
    calcular_notas_finales,
    calcular_ranking,
    detectar_tp_sin_corregir,
    es_atrasado,
)
from app.repositories.analisis_repository import AnalisisRepository
from app.repositories.asignacion_repository import AsignacionRepository


def _get_cipher() -> AES256GCMCipher:
    """Instancia el cipher AES-256 desde las settings."""
    settings = Settings()
    return AES256GCMCipher(derive_encryption_key(settings.encryption_key))


_ROLES_SCOPE_PROPIO = {"PROFESOR", "TUTOR"}
_ROLES_SCOPE_GLOBAL = {"COORDINADOR", "ADMIN"}


class AnalisisService:
    def __init__(
        self,
        analisis_repo: AnalisisRepository,
        asignacion_repo: AsignacionRepository,
        session: AsyncSession,
    ) -> None:
        self._analisis_repo = analisis_repo
        self._asignacion_repo = asignacion_repo
        self._session = session

    async def _resolver_asignacion_id(
        self,
        usuario_id: uuid.UUID,
        materia_id: uuid.UUID,
        tenant_id: uuid.UUID,
    ) -> Optional[uuid.UUID]:
        """Resuelve la asignacion_id activa del usuario para la materia."""
        asignaciones = await self._asignacion_repo.list_vigentes(
            tenant_id=tenant_id,
            user_id=usuario_id,
        )
        for asig in asignaciones:
            if asig.materia_id == materia_id:
                return asig.id
        return None

    def _tiene_scope_propio(self, current_user: CurrentUser) -> bool:
        return bool(set(current_user.roles) & _ROLES_SCOPE_PROPIO)

    def _tiene_scope_global(self, current_user: CurrentUser) -> bool:
        return bool(set(current_user.roles) & _ROLES_SCOPE_GLOBAL)

    async def _get_alumnos(
        self,
        materia_id: uuid.UUID,
        current_user: CurrentUser,
        cipher=None,
    ) -> list[AlumnoCalificacionesDTO]:
        """Carga alumnos con calificaciones respetando el scope del usuario."""
        if cipher is None:
            try:
                cipher = _get_cipher()
            except Exception:
                cipher = None

        if self._tiene_scope_global(current_user):
            return await self._analisis_repo.get_calificaciones_por_materia(
                materia_id=materia_id,
                tenant_id=current_user.tenant_id,
                cipher=cipher,
            )

        # PROFESOR / TUTOR → solo sus alumnos
        asignacion_id = await self._resolver_asignacion_id(
            usuario_id=current_user.id,
            materia_id=materia_id,
            tenant_id=current_user.tenant_id,
        )
        if asignacion_id is None:
            return []

        return await self._analisis_repo.get_calificaciones_por_asignacion(
            asignacion_id=asignacion_id,
            materia_id=materia_id,
            tenant_id=current_user.tenant_id,
            cipher=cipher,
        )

    # ── get_atrasados ─────────────────────────────────────────────────────────

    async def get_atrasados(
        self,
        materia_id: uuid.UUID,
        actividades_seleccionadas: list[str],
        current_user: CurrentUser,
    ) -> dict:
        """Computa alumnos atrasados para la materia y actividades dadas."""
        alumnos = await self._get_alumnos(materia_id, current_user)

        # Resolver umbral — si hay scope propio, usamos asignacion_id del PROFESOR
        umbral_pct = 60
        valores_aprobatorios: list[str] = []
        if self._tiene_scope_propio(current_user):
            asig_id = await self._resolver_asignacion_id(
                current_user.id, materia_id, current_user.tenant_id
            )
            if asig_id:
                umbral_dto = await self._analisis_repo.get_umbral(
                    asig_id, materia_id, current_user.tenant_id
                )
                umbral_pct = umbral_dto.umbral_pct
                valores_aprobatorios = umbral_dto.valores_aprobatorios

        items = []
        for alumno in alumnos:
            atrasado, faltantes, bajo = es_atrasado(
                calificaciones=alumno.calificaciones,
                actividades_seleccionadas=actividades_seleccionadas,
                umbral_pct=umbral_pct,
                valores_aprobatorios=valores_aprobatorios,
            )
            if atrasado:
                items.append({
                    "entrada_padron_id": alumno.entrada_padron_id,
                    "nombre": alumno.nombre,
                    "apellidos": alumno.apellidos,
                    "email": alumno.email,
                    "comision": alumno.comision,
                    "actividades_faltantes": faltantes,
                    "actividades_bajo_umbral": bajo,
                })

        return {"total_atrasados": len(items), "items": items}

    # ── get_ranking ───────────────────────────────────────────────────────────

    async def get_ranking(
        self,
        materia_id: uuid.UUID,
        current_user: CurrentUser,
    ) -> dict:
        """Ranking de alumnos por actividades aprobadas (RN-09)."""
        alumnos = await self._get_alumnos(materia_id, current_user)

        umbral_pct = 60
        valores_aprobatorios: list[str] = []
        if self._tiene_scope_propio(current_user):
            asig_id = await self._resolver_asignacion_id(
                current_user.id, materia_id, current_user.tenant_id
            )
            if asig_id:
                umbral_dto = await self._analisis_repo.get_umbral(
                    asig_id, materia_id, current_user.tenant_id
                )
                umbral_pct = umbral_dto.umbral_pct
                valores_aprobatorios = umbral_dto.valores_aprobatorios

        items = calcular_ranking(alumnos, umbral_pct, valores_aprobatorios)
        return {"total": len(items), "items": items}

    # ── get_reporte_rapido ────────────────────────────────────────────────────

    async def get_reporte_rapido(
        self,
        materia_id: uuid.UUID,
        current_user: CurrentUser,
    ) -> dict:
        """Métricas agregadas: total alumnos, atrasados, pct aprobación por actividad."""
        alumnos = await self._get_alumnos(materia_id, current_user)

        umbral_pct = 60
        valores_aprobatorios: list[str] = []
        if self._tiene_scope_propio(current_user):
            asig_id = await self._resolver_asignacion_id(
                current_user.id, materia_id, current_user.tenant_id
            )
            if asig_id:
                umbral_dto = await self._analisis_repo.get_umbral(
                    asig_id, materia_id, current_user.tenant_id
                )
                umbral_pct = umbral_dto.umbral_pct
                valores_aprobatorios = umbral_dto.valores_aprobatorios

        from app.domain.aprobado import derivar_aprobado

        # Obtener todas las actividades
        actividades_set: set[str] = set()
        for a in alumnos:
            for c in a.calificaciones:
                actividades_set.add(c.actividad)

        # Métricas por actividad
        metricas: dict[str, dict] = {
            act: {"actividad": act, "total_calificados": 0, "total_aprobados": 0}
            for act in actividades_set
        }

        total_atrasados = 0
        for alumno in alumnos:
            tiene_atraso = False
            for c in alumno.calificaciones:
                metricas[c.actividad]["total_calificados"] += 1
                aprobado = derivar_aprobado(
                    nota_numerica=c.nota_numerica,
                    nota_textual=c.nota_textual,
                    umbral_pct=umbral_pct,
                    nota_maxima=10.0,
                    valores_aprobatorios=valores_aprobatorios,
                )
                if aprobado:
                    metricas[c.actividad]["total_aprobados"] += 1
                else:
                    tiene_atraso = True
            if tiene_atraso or not alumno.calificaciones:
                total_atrasados += 1

        for m in metricas.values():
            total_cal = m["total_calificados"]
            m["pct_aprobacion"] = (
                round(m["total_aprobados"] / total_cal * 100, 2) if total_cal > 0 else 0.0
            )

        return {
            "total_alumnos": len(alumnos),
            "total_atrasados": total_atrasados,
            "actividades_count": len(actividades_set),
            "metricas_por_actividad": list(metricas.values()),
        }

    # ── get_notas_finales ─────────────────────────────────────────────────────

    async def get_notas_finales(
        self,
        materia_id: uuid.UUID,
        actividades_seleccionadas: list[str],
        current_user: CurrentUser,
    ) -> dict:
        """Nota final por alumno sumando actividades seleccionadas."""
        alumnos = await self._get_alumnos(materia_id, current_user)
        items = calcular_notas_finales(alumnos, actividades_seleccionadas)
        return {"actividades_seleccionadas": actividades_seleccionadas, "items": items}

    # ── detectar_tp_sin_corregir ──────────────────────────────────────────────

    async def detectar_tp_sin_corregir(
        self,
        materia_id: uuid.UUID,
        csv_bytes: bytes,
        current_user: CurrentUser,
    ) -> list[dict]:
        """Detecta TPs finalizados sin corrección textual.

        Parsea el CSV en streaming. Columnas esperadas: entrada_padron_id, actividad, estado.
        Si las columnas son distintas, intenta inferir por posición.
        """
        alumnos = await self._get_alumnos(materia_id, current_user)

        finalizaciones: list[FinalizacionDTO] = []
        text = csv_bytes.decode("utf-8", errors="replace")
        reader = csv.DictReader(io.StringIO(text))
        for row in reader:
            try:
                ep_id = uuid.UUID(row.get("entrada_padron_id", "").strip())
                actividad = row.get("actividad", "").strip()
                estado = row.get("estado", "").strip()
                if actividad and estado:
                    finalizaciones.append(FinalizacionDTO(ep_id, actividad, estado))
            except (ValueError, AttributeError):
                continue

        return detectar_tp_sin_corregir(alumnos, finalizaciones)

    # ── get_monitor ───────────────────────────────────────────────────────────

    async def get_monitor(
        self,
        materia_id: uuid.UUID,
        current_user: CurrentUser,
        filtros=None,
        request=None,
    ) -> dict:
        """Monitor general (COORD/ADMIN) o de seguimiento (TUTOR/PROFESOR)."""
        umbral_pct = 60
        valores_aprobatorios: list[str] = []

        if self._tiene_scope_global(current_user):
            # Monitor general — genera auditoría
            alumnos = await self._analisis_repo.get_monitor_general(
                materia_id=materia_id,
                tenant_id=current_user.tenant_id,
                filtros=filtros,
                cipher=None,
            )
            await record_audit(
                session=self._session,
                current_user=current_user,
                action=ANALISIS_ATRASADOS_VER,
                request=request,
                materia_id=materia_id,
            )
        else:
            # Monitor seguimiento — scope propio
            asig_id = await self._resolver_asignacion_id(
                current_user.id, materia_id, current_user.tenant_id
            )
            if asig_id is None:
                return {"total": 0, "items": []}
            alumnos = await self._analisis_repo.get_monitor_seguimiento(
                asignacion_id=asig_id,
                materia_id=materia_id,
                tenant_id=current_user.tenant_id,
                filtros=filtros,
                cipher=None,
            )
            umbral_dto = await self._analisis_repo.get_umbral(
                asig_id, materia_id, current_user.tenant_id
            )
            umbral_pct = umbral_dto.umbral_pct
            valores_aprobatorios = umbral_dto.valores_aprobatorios

        from app.domain.aprobado import derivar_aprobado

        # Aplicar filtro min_actividades_cumplidas
        min_actividades = getattr(filtros, "min_actividades_cumplidas", None)

        items = []
        for alumno in alumnos:
            aprobadas = sum(
                1 for c in alumno.calificaciones
                if derivar_aprobado(
                    nota_numerica=c.nota_numerica,
                    nota_textual=c.nota_textual,
                    umbral_pct=umbral_pct,
                    nota_maxima=10.0,
                    valores_aprobatorios=valores_aprobatorios,
                )
            )
            pendientes = len(alumno.calificaciones) - aprobadas

            if min_actividades is not None and aprobadas < min_actividades:
                continue

            _, faltantes, bajo = es_atrasado(
                calificaciones=alumno.calificaciones,
                actividades_seleccionadas=[c.actividad for c in alumno.calificaciones],
                umbral_pct=umbral_pct,
                valores_aprobatorios=valores_aprobatorios,
            )
            atrasado = bool(faltantes or bajo)

            items.append({
                "entrada_padron_id": alumno.entrada_padron_id,
                "nombre": alumno.nombre,
                "apellidos": alumno.apellidos,
                "comision": alumno.comision,
                "actividades_aprobadas": aprobadas,
                "actividades_pendientes": pendientes,
                "es_atrasado": atrasado,
            })

        return {"total": len(items), "items": items}
