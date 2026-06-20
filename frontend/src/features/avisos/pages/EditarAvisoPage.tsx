import { useNavigate, useParams } from 'react-router-dom'
import { AvisoForm, avisoToFormDefaults } from '../components/AvisoForm'
import { useAviso, useEditarAviso } from '../hooks/useAvisos'
import type { AvisoFormSchema } from '../components/avisoSchema'

export function EditarAvisoPage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const { data: aviso, isLoading } = useAviso(id ?? '')
  const mutation = useEditarAviso(id ?? '')

  async function handleSubmit(data: AvisoFormSchema) {
    await mutation.mutateAsync(data)
    navigate('/avisos')
  }

  if (isLoading) return <p className="text-gray-500">Cargando aviso…</p>
  if (!aviso) return <p className="text-red-600">Aviso no encontrado.</p>

  return (
    <div>
      <h1 className="text-2xl font-bold text-gray-900 mb-6">Editar Aviso</h1>
      <AvisoForm
        defaultValues={avisoToFormDefaults(aviso)}
        onSubmit={handleSubmit}
        isSubmitting={mutation.isPending}
      />
    </div>
  )
}
