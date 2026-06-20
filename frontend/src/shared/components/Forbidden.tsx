export function Forbidden() {
  return (
    <div className="flex min-h-screen items-center justify-center bg-gray-50">
      <div className="text-center">
        <h1 className="text-6xl font-bold text-red-500">403</h1>
        <h2 className="mt-4 text-2xl font-semibold text-gray-800">Acceso denegado</h2>
        <p className="mt-2 text-gray-600">
          No tenés permiso para acceder a esta sección.
        </p>
      </div>
    </div>
  )
}
