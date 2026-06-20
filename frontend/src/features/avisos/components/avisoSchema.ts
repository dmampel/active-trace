import { z } from 'zod'

export const avisoSchema = z
  .object({
    scope: z.enum(['global', 'materia', 'cohorte'] as const),
    roles: z.array(z.string()).min(1, 'Seleccioná al menos un rol'),
    severidad: z.enum(['info', 'advertencia', 'critico'] as const),
    titulo: z.string().min(1, 'Título requerido').max(200),
    cuerpo: z.string().min(1, 'Cuerpo requerido'),
    vigenciaDesde: z.string().min(1, 'Fecha de inicio requerida'),
    vigenciaHasta: z.string().optional(),
    orden: z.number().int().min(0).default(0),
    requireAck: z.boolean().default(false),
    materiaId: z.string().optional(),
    cohorteId: z.string().optional(),
  })
  .superRefine((data, ctx) => {
    if (data.scope === 'materia' || data.scope === 'cohorte') {
      if (!data.materiaId) {
        ctx.addIssue({
          code: z.ZodIssueCode.custom,
          message: 'Materia requerida para este scope',
          path: ['materiaId'],
        })
      }
    }
    if (data.scope === 'cohorte') {
      if (!data.cohorteId) {
        ctx.addIssue({
          code: z.ZodIssueCode.custom,
          message: 'Cohorte requerida para scope cohorte',
          path: ['cohorteId'],
        })
      }
    }
  })

export type AvisoFormSchema = z.infer<typeof avisoSchema>
