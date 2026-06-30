import { useEffect, useState } from 'react'

type Health = {
  status: string
  database: string
  service: string
}

const apiBaseUrl = import.meta.env.VITE_API_BASE_URL ?? 'http://127.0.0.1:8000'

function App() {
  const [health, setHealth] = useState<Health | null>(null)
  const [error, setError] = useState(false)

  useEffect(() => {
    const controller = new AbortController()

    fetch(`${apiBaseUrl}/health`, { signal: controller.signal })
      .then((response) => {
        if (!response.ok) throw new Error('Engine health check failed')
        return response.json() as Promise<Health>
      })
      .then(setHealth)
      .catch((requestError: unknown) => {
        if (requestError instanceof DOMException && requestError.name === 'AbortError') return
        setError(true)
      })

    return () => controller.abort()
  }, [])

  const connected = health?.status === 'ok' && health.database === 'ready'

  return (
    <main>
      <section className="shell" aria-labelledby="page-title">
        <p className="product-mark">
          <span aria-hidden="true">DF</span>
          Local engineering orchestration
        </p>
        <h1 id="page-title">DevFlow Assistant</h1>
        <p className="lede">
          The workspace is standing by. Phase 0 connects the interface to a
          deterministic local engine and its SQLite state store.
        </p>

        <div className="status-panel" role="status" aria-live="polite">
          <span
            className={`signal ${connected ? 'signal--ready' : error ? 'signal--error' : ''}`}
            aria-hidden="true"
          />
          <div>
            <strong>
              {connected
                ? 'Engine connected'
                : error
                  ? 'Engine unavailable'
                  : 'Checking local engine…'}
            </strong>
            <p>
              {connected
                ? 'FastAPI is responding and the full SQLite schema is ready.'
                : error
                  ? `Start the engine at ${apiBaseUrl}, then refresh this page.`
                  : 'Verifying the API and database.'}
            </p>
          </div>
        </div>
      </section>
    </main>
  )
}

export default App
