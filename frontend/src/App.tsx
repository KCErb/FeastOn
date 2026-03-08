import { useQuery } from '@tanstack/react-query'

function App() {
  const { data: health, isLoading } = useQuery({
    queryKey: ['health'],
    queryFn: async () => {
      const response = await fetch('/api/health')
      if (!response.ok) throw new Error('Health check failed')
      return response.json()
    },
  })

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100">
      <div className="container mx-auto px-4 py-16">
        <div className="max-w-2xl mx-auto">
          <h1 className="text-4xl font-bold text-slate-900 mb-4">
            FeastOn
          </h1>
          <p className="text-lg text-slate-600 mb-8">
            Feast upon the words of Christ — in any language
          </p>

          <div className="bg-white rounded-lg shadow-md p-6 mb-6">
            <h2 className="text-xl font-semibold text-slate-800 mb-3">
              Backend Status
            </h2>
            {isLoading ? (
              <p className="text-slate-500">Checking backend connection...</p>
            ) : health ? (
              <div className="space-y-2">
                <p className="text-green-600 font-medium">✓ Connected</p>
                <p className="text-sm text-slate-600">
                  Version: {health.version}
                </p>
                <p className="text-sm text-slate-600">
                  Data directory: {health.data_dir}
                </p>
              </div>
            ) : (
              <p className="text-red-600">✗ Backend not available</p>
            )}
          </div>

          <div className="bg-white rounded-lg shadow-md p-6">
            <h2 className="text-xl font-semibold text-slate-800 mb-3">
              Project Status
            </h2>
            <div className="space-y-3">
              <StatusItem
                label="Pipeline CLI"
                status="ready"
                description="Run 'conflang --help' to see available commands"
              />
              <StatusItem
                label="Backend API"
                status="ready"
                description="FastAPI server with provider interfaces"
              />
              <StatusItem
                label="Frontend Shell"
                status="ready"
                description="React + TypeScript + Tailwind CSS + TanStack Query"
              />
              <StatusItem
                label="Pipeline Stages"
                status="pending"
                description="8 stages (not yet implemented)"
              />
              <StatusItem
                label="Study UI"
                status="pending"
                description="Read & Listen, Interlinear, Word Exploration"
              />
            </div>
          </div>

          <div className="mt-8 text-center text-sm text-slate-500">
            <p>Ready to build features</p>
            <p className="mt-1">See CLAUDE.md for implementation plan</p>
          </div>
        </div>
      </div>
    </div>
  )
}

function StatusItem({
  label,
  status,
  description,
}: {
  label: string
  status: 'ready' | 'pending'
  description: string
}) {
  return (
    <div className="flex items-start gap-3">
      <span
        className={`mt-1 flex-shrink-0 w-2 h-2 rounded-full ${
          status === 'ready' ? 'bg-green-500' : 'bg-amber-400'
        }`}
      />
      <div>
        <p className="font-medium text-slate-800">{label}</p>
        <p className="text-sm text-slate-600">{description}</p>
      </div>
    </div>
  )
}

export default App
