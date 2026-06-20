export type EstadoTarea = 'abierta' | 'en_progreso' | 'completada' | 'rechazada'

export interface ComentarioTarea {
  id: string
  tareaId: string
  autorId: string
  autorNombre: string
  autorApellido: string
  texto: string
  creadoEn: string
}

export interface Tarea {
  id: string
  titulo: string
  descripcion: string
  estado: EstadoTarea
  materiaId: string
  materiaNombre: string
  asignadoAId: string
  asignadoANombre: string
  asignadoAApellido: string
  asignadoPorId: string
  asignadoPorNombre: string
  asignadoPorApellido: string
  comentarios: ComentarioTarea[]
  creadaEn: string
  actualizadaEn: string
}

export interface FiltrosTareas {
  estado?: EstadoTarea
  docenteId?: string
  materiaId?: string
  asignadoPorId?: string
  page?: number
  pageSize?: number
}

export interface AgregarComentarioPayload {
  texto: string
}

export interface CambiarEstadoPayload {
  estado: EstadoTarea
  comentario?: string
}
