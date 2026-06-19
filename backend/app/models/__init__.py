from app.models.base import Base, UUIDMixin, TimestampMixin, SoftDeleteMixin, TenantMixin
from app.models.tenant import Tenant
from app.models.user import User, RefreshToken, PasswordResetToken
from app.models.rbac import Rol, Permiso, RolPermiso, UserRol
from app.models.audit_log import AuditLog
from app.models.estructura import Carrera, Cohorte, EstadoEntidad, InstanciaDictado, Materia
from app.models.asignacion import Asignacion, RolDominio
from app.models.padron import VersionPadron, EntradaPadron
from app.models.tenant_moodle_config import TenantMoodleConfig
from app.models.calificacion import Calificacion, UmbralMateria, OrigenCalificacion
from app.models.comunicacion import Comunicacion, EstadoComunicacion, validar_transicion
from app.models.encuentro import (
    DiaSemana,
    EstadoInstanciaEncuentro,
    InstanciaEncuentro,
    SlotEncuentro,
)
from app.models.guardia import EstadoGuardia, Guardia
from app.models.evaluacion import (
    TipoEvaluacion,
    EstadoReserva,
    TipoFechaAcademica,
    Evaluacion,
    EvaluacionAlumno,
    ReservaEvaluacion,
    ResultadoEvaluacion,
    FechaAcademica,
)
from app.models.aviso import AlcanceAviso, SeveridadAviso, Aviso, AcknowledgmentAviso

__all__ = [
    "Base",
    "UUIDMixin",
    "TimestampMixin",
    "SoftDeleteMixin",
    "TenantMixin",
    "Tenant",
    "User",
    "RefreshToken",
    "PasswordResetToken",
    "Rol",
    "Permiso",
    "RolPermiso",
    "UserRol",
    "AuditLog",
    "Carrera",
    "Cohorte",
    "EstadoEntidad",
    "InstanciaDictado",
    "Materia",
    "Asignacion",
    "RolDominio",
    "VersionPadron",
    "EntradaPadron",
    "TenantMoodleConfig",
    "Calificacion",
    "UmbralMateria",
    "OrigenCalificacion",
    "Comunicacion",
    "EstadoComunicacion",
    "validar_transicion",
    "DiaSemana",
    "EstadoInstanciaEncuentro",
    "SlotEncuentro",
    "InstanciaEncuentro",
    "EstadoGuardia",
    "Guardia",
    "TipoEvaluacion",
    "EstadoReserva",
    "TipoFechaAcademica",
    "Evaluacion",
    "EvaluacionAlumno",
    "ReservaEvaluacion",
    "ResultadoEvaluacion",
    "FechaAcademica",
    "AlcanceAviso",
    "SeveridadAviso",
    "Aviso",
    "AcknowledgmentAviso",
]
