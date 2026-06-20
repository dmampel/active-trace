import { useNavigate } from 'react-router-dom'
import { AvisoForm } from '../components/AvisoForm'
import { useCrearAviso } from '../hooks/useAvisos'
import type { AvisoFormSchema } from '../components/avisoSchema'

export function NuevoAvisoPage() {
  const navigate = useNavigate()
  const mutation = useCrearAviso()

  async function handleSubmit(data: AvisoFormSchema) {
    await mutation.mutateAsync(data)
    navigate('/avisos')
  }

  return (
    <div>
      <h1 className="text-2xl font-bold text-gray-900 mb-6">Nuevo Aviso</h1>
      <AvisoForm onSubmit={handleSubmit} isSubmitting={mutation.isPending} />
    </div>
  )
}
