import { FormEvent, useCallback, useEffect, useMemo, useState } from 'react'

type Project = {
  id: number
  name: string
  root_path: string
  summary: string | null
  languages: string[]
  scan_type: 'soft' | 'hard' | null
}

type RequestSummary = {
  request_id: string
  project_id: number
  original_text: string
  state: string
  created_at: string
}

type Task = {
  task_id: string
  description: string
  priority: string
  acceptance_criteria: string[]
}

type StageResult = {
  id: number
  stage: string
  output: Record<string, unknown>
  confidence: number
  risk_level: string
  status: string
  duration_ms: number
}

type HistoryEntry = {
  id: number
  stage: string | null
  event: string
  created_at: string
  detail: string | null
}

type RequestDetail = RequestSummary & {
  planner_interpretation: string | null
  tasks: Task[]
  stage_results: StageResult[]
  history: HistoryEntry[]
  approval: { reason: string; stage: string } | null
  final_report: { verdict: string; report: string } | null
  next_stage: string | null
}

type EvidenceTab = 'output' | 'tasks' | 'tests' | 'history'

const apiBaseUrl = import.meta.env.VITE_API_BASE_URL ?? 'http://127.0.0.1:8000'

const stages = [
  ['request_logger', 'Request logger'],
  ['planner', 'Planner'],
  ['repo_analyzer', 'Repository analyzer'],
  ['builder', 'Builder'],
  ['documentation', 'Documentation'],
  ['tester', 'Tester'],
  ['reviewer', 'Reviewer'],
  ['final_report', 'Final report'],
] as const

const terminalStates = new Set(['DONE', 'FAILED', 'REJECTED'])

async function api<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`${apiBaseUrl}${path}`, {
    ...options,
    headers: { 'Content-Type': 'application/json', ...options?.headers },
  })
  if (!response.ok) {
    const body = (await response.json().catch(() => null)) as
      | { detail?: string }
      | null
    throw new Error(body?.detail ?? `Request failed (${response.status})`)
  }
  return response.json() as Promise<T>
}

function App() {
  const [engineReady, setEngineReady] = useState(false)
  const [projects, setProjects] = useState<Project[]>([])
  const [projectId, setProjectId] = useState<number | null>(null)
  const [requests, setRequests] = useState<RequestSummary[]>([])
  const [activeRequest, setActiveRequest] = useState<RequestDetail | null>(null)
  const [tab, setTab] = useState<EvidenceTab>('output')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [showProjectForm, setShowProjectForm] = useState(false)

  const selectedProject = projects.find((project) => project.id === projectId)

  const refreshProjects = useCallback(async () => {
    const items = await api<Project[]>('/api/projects')
    setProjects(items)
    setProjectId((current) => current ?? items[0]?.id ?? null)
  }, [])

  const refreshRequests = useCallback(async (selectedId: number) => {
    const items = await api<RequestSummary[]>(
      `/api/projects/${selectedId}/requests`,
    )
    setRequests(items)
  }, [])

  useEffect(() => {
    Promise.all([api<{ status: string }>('/health'), refreshProjects()])
      .then(([health]) => setEngineReady(health.status === 'ok'))
      .catch((cause: unknown) =>
        setError(cause instanceof Error ? cause.message : 'Engine unavailable'),
      )
  }, [refreshProjects])

  useEffect(() => {
    if (projectId) {
      refreshRequests(projectId).catch((cause: unknown) =>
        setError(cause instanceof Error ? cause.message : 'Could not load requests'),
      )
    } else {
      setRequests([])
      setActiveRequest(null)
    }
  }, [projectId, refreshRequests])

  const runAction = async (action: () => Promise<void>) => {
    setBusy(true)
    setError('')
    try {
      await action()
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'The action failed')
    } finally {
      setBusy(false)
    }
  }

  const createProject = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    const form = new FormData(event.currentTarget)
    void runAction(async () => {
      const project = await api<Project>('/api/projects', {
        method: 'POST',
        body: JSON.stringify({
          name: form.get('name'),
          root_path: form.get('root_path'),
          scan_type: 'soft',
        }),
      })
      await refreshProjects()
      setProjectId(project.id)
      setShowProjectForm(false)
    })
  }

  const scanProject = (scanType: 'soft' | 'hard') => {
    if (!projectId) return
    void runAction(async () => {
      await api(`/api/projects/${projectId}/scan`, {
        method: 'POST',
        body: JSON.stringify({ scan_type: scanType }),
      })
      await refreshProjects()
    })
  }

  const createRequest = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    if (!projectId) return
    const form = event.currentTarget
    const data = new FormData(form)
    void runAction(async () => {
      const detail = await api<RequestDetail>('/api/requests', {
        method: 'POST',
        body: JSON.stringify({
          project_id: projectId,
          original_text: data.get('original_text'),
        }),
      })
      setActiveRequest(detail)
      form.reset()
      await refreshRequests(projectId)
    })
  }

  const openRequest = (requestId: string) => {
    void runAction(async () => {
      setActiveRequest(await api<RequestDetail>(`/api/requests/${requestId}`))
    })
  }

  const runPipeline = () => {
    if (!activeRequest) return
    void runAction(async () => {
      let detail = activeRequest
      for (let index = 0; index < 10; index += 1) {
        if (
          terminalStates.has(detail.state) ||
          detail.state === 'AWAITING_APPROVAL'
        ) {
          break
        }
        detail = await api<RequestDetail>(
          `/api/requests/${detail.request_id}/advance`,
          {
            method: 'POST',
            body: JSON.stringify({ provider_id: 'mock' }),
          },
        )
        setActiveRequest(detail)
      }
      await refreshRequests(detail.project_id)
    })
  }

  const decide = (action: 'approve' | 'reject') => {
    if (!activeRequest) return
    void runAction(async () => {
      const detail = await api<RequestDetail>(
        `/api/requests/${activeRequest.request_id}/approval`,
        {
          method: 'POST',
          body: JSON.stringify({ action, decided_by: 'local-user' }),
        },
      )
      setActiveRequest(detail)
      if (projectId) await refreshRequests(projectId)
    })
  }

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <a className="brand" href="#workspace" aria-label="DevFlow workspace">
          <span className="brand-mark" aria-hidden="true">D</span>
          <span>DevFlow<small>Assistant</small></span>
        </a>

        <div className="project-switcher">
          <label htmlFor="project">Project</label>
          <select
            id="project"
            value={projectId ?? ''}
            onChange={(event) => {
              setProjectId(Number(event.target.value))
              setActiveRequest(null)
            }}
          >
            {!projects.length && <option value="">No projects</option>}
            {projects.map((project) => (
              <option key={project.id} value={project.id}>{project.name}</option>
            ))}
          </select>
        </div>

        <nav aria-label="Workspace">
          <a className="nav-item nav-item--active" href="#pipeline">
            <span aria-hidden="true">⌘</span> Pipeline
          </a>
          <a className="nav-item" href="#requests">
            <span aria-hidden="true">≡</span> Requests
          </a>
        </nav>

        <div className="engine-status">
          <span className={engineReady ? 'dot dot--success' : 'dot dot--danger'} />
          <span>Local engine</span>
          <small>{engineReady ? 'Ready' : 'Offline'}</small>
        </div>
      </aside>

      <main id="workspace">
        <header className="workspace-bar">
          <div>
            <span className="crumb">{selectedProject?.name ?? 'Workspace'}</span>
            <span className="slash">/</span>
            <span>Pipeline</span>
          </div>
          <div className="toolbar">
            {selectedProject && (
              <>
                <button
                  className="button button--quiet"
                  disabled={busy}
                  onClick={() => scanProject('soft')}
                >
                  Refresh context
                </button>
                <button
                  className="button button--secondary"
                  disabled={busy}
                  onClick={() => scanProject('hard')}
                >
                  Scan workspace
                </button>
              </>
            )}
            <button
              className="button button--primary"
              onClick={() => setShowProjectForm((visible) => !visible)}
            >
              Add project
            </button>
          </div>
        </header>

        {error && (
          <div className="error-banner" role="alert">
            <strong>Action could not be completed.</strong>
            <span>{error}</span>
            <button onClick={() => setError('')} aria-label="Dismiss error">×</button>
          </div>
        )}

        {showProjectForm && (
          <form className="project-form" onSubmit={createProject}>
            <div>
              <label htmlFor="project-name">Project name</label>
              <input id="project-name" name="name" required placeholder="Work Assistant" />
            </div>
            <div className="field-wide">
              <label htmlFor="root-path">Local repository path</label>
              <input
                id="root-path"
                name="root_path"
                required
                placeholder="E:\Projects\Work Assistant"
              />
            </div>
            <button className="button button--primary" disabled={busy}>
              Add and soft scan
            </button>
          </form>
        )}

        {!selectedProject ? (
          <EmptyWorkspace onAdd={() => setShowProjectForm(true)} />
        ) : (
          <div className="workspace-grid">
            <section className="request-column" id="pipeline">
              <RequestComposer busy={busy} onSubmit={createRequest} />
              <RequestList
                requests={requests}
                activeId={activeRequest?.request_id}
                onOpen={openRequest}
              />
              {activeRequest && (
                <Pipeline
                  detail={activeRequest}
                  busy={busy}
                  onRun={runPipeline}
                  onDecide={decide}
                />
              )}
            </section>

            <EvidenceInspector
              detail={activeRequest}
              tab={tab}
              onTab={setTab}
            />
          </div>
        )}
      </main>
    </div>
  )
}

function EmptyWorkspace({ onAdd }: { onAdd: () => void }) {
  return (
    <section className="empty-workspace">
      <span className="empty-mark" aria-hidden="true">⌁</span>
      <h1>Connect a local project</h1>
      <p>
        DevFlow starts with a soft scan of the repository’s Markdown knowledge
        base. Your source and workflow state stay on this machine.
      </p>
      <button className="button button--primary" onClick={onAdd}>Add project</button>
    </section>
  )
}

function RequestComposer({
  busy,
  onSubmit,
}: {
  busy: boolean
  onSubmit: (event: FormEvent<HTMLFormElement>) => void
}) {
  return (
    <form className="request-composer" id="requests" onSubmit={onSubmit}>
      <label htmlFor="request-text">New engineering request</label>
      <textarea
        id="request-text"
        name="original_text"
        required
        rows={3}
        placeholder="Describe the outcome, constraints, and acceptance expectations…"
      />
      <div className="composer-footer">
        <span>Original text is preserved verbatim.</span>
        <button className="button button--primary" disabled={busy}>
          Log request
        </button>
      </div>
    </form>
  )
}

function RequestList({
  requests,
  activeId,
  onOpen,
}: {
  requests: RequestSummary[]
  activeId?: string
  onOpen: (id: string) => void
}) {
  if (!requests.length) return null
  return (
    <section className="request-list" aria-label="Recent requests">
      <div className="section-heading">
        <h2>Requests</h2><span>{requests.length}</span>
      </div>
      {requests.map((request) => (
        <button
          key={request.request_id}
          className={`request-row ${activeId === request.request_id ? 'request-row--active' : ''}`}
          onClick={() => onOpen(request.request_id)}
        >
          <code>{request.request_id}</code>
          <span className="request-copy">{request.original_text}</span>
          <StateLabel state={request.state} />
        </button>
      ))}
    </section>
  )
}

function Pipeline({
  detail,
  busy,
  onRun,
  onDecide,
}: {
  detail: RequestDetail
  busy: boolean
  onRun: () => void
  onDecide: (action: 'approve' | 'reject') => void
}) {
  const resultByStage = useMemo(
    () => new Map(detail.stage_results.map((result) => [result.stage, result])),
    [detail.stage_results],
  )
  return (
    <section className="pipeline" aria-labelledby="pipeline-title">
      <div className="request-header">
        <div>
          <code>{detail.request_id}</code>
          <h1 id="pipeline-title">{detail.original_text}</h1>
        </div>
        <StateLabel state={detail.state} />
      </div>

      <ol className="stage-list">
        {stages.map(([key, label], index) => {
          const result = resultByStage.get(key)
          const active = detail.next_stage === key
          return (
            <li
              key={key}
              className={`stage ${result ? 'stage--complete' : ''} ${active ? 'stage--active' : ''}`}
            >
              <span className="stage-index">{result ? '✓' : index + 1}</span>
              <div><strong>{label}</strong><small>{key}</small></div>
              <span className="stage-state">
                {result ? result.status : active ? 'Ready' : 'Waiting'}
              </span>
              <code>{result ? `${result.duration_ms} ms` : '—'}</code>
            </li>
          )
        })}
      </ol>

      {detail.approval && (
        <div className="approval-panel">
          <div className="approval-title">
            <span aria-hidden="true">!</span>
            <div><strong>Approval required</strong><small>{detail.approval.stage}</small></div>
          </div>
          <p>{detail.approval.reason}</p>
          <div className="approval-actions">
            <button className="button button--approve" disabled={busy} onClick={() => onDecide('approve')}>
              Approve and continue
            </button>
            <button className="button button--danger" disabled={busy} onClick={() => onDecide('reject')}>
              Reject request
            </button>
          </div>
        </div>
      )}

      {!terminalStates.has(detail.state) && detail.state !== 'AWAITING_APPROVAL' && (
        <div className="pipeline-actions">
          <div>
            <strong>{busy ? 'Running deterministic pipeline…' : `Next: ${detail.next_stage ?? 'complete'}`}</strong>
            <small>Provider: Mock · eligible for all tiers</small>
          </div>
          <button className="button button--primary" disabled={busy} onClick={onRun}>
            {busy ? 'Running…' : 'Run pipeline'}
          </button>
        </div>
      )}
    </section>
  )
}

function EvidenceInspector({
  detail,
  tab,
  onTab,
}: {
  detail: RequestDetail | null
  tab: EvidenceTab
  onTab: (tab: EvidenceTab) => void
}) {
  const latest = detail?.stage_results.at(-1)
  const tabs: [EvidenceTab, string][] = [
    ['output', 'Output'],
    ['tasks', 'Tasks'],
    ['tests', 'Tests'],
    ['history', 'History'],
  ]
  return (
    <aside className="inspector" aria-label="Request evidence">
      <div className="tab-list" role="tablist">
        {tabs.map(([key, label]) => (
          <button
            key={key}
            role="tab"
            aria-selected={tab === key}
            onClick={() => onTab(key)}
          >
            {label}
          </button>
        ))}
      </div>
      {!detail ? (
        <div className="inspector-empty">
          <span aria-hidden="true">↗</span>
          <h2>Select a request</h2>
          <p>Stage output, tasks, tests, and immutable history appear here.</p>
        </div>
      ) : (
        <div className="inspector-content">
          {tab === 'output' && (
            <>
              <div className="section-heading">
                <h2>Stage output</h2>
                <span>{latest?.stage ?? 'No result'}</span>
              </div>
              <pre>{JSON.stringify(latest?.output ?? {}, null, 2)}</pre>
              {detail.final_report && (
                <section className="final-report">
                  <span className="status-chip status-chip--success">Complete</span>
                  <h2>Final report</h2>
                  <p>{detail.final_report.report}</p>
                </section>
              )}
            </>
          )}
          {tab === 'tasks' && (
            <div className="evidence-list">
              <div className="section-heading"><h2>Planned tasks</h2><span>{detail.tasks.length}</span></div>
              {detail.tasks.map((task) => (
                <article key={task.task_id}>
                  <code>{task.task_id}</code>
                  <strong>{task.description}</strong>
                  <ul>{task.acceptance_criteria.map((criterion) => <li key={criterion}>{criterion}</li>)}</ul>
                </article>
              ))}
              {!detail.tasks.length && <p className="empty-copy">Tasks appear after planning.</p>}
            </div>
          )}
          {tab === 'tests' && (
            <TestEvidence results={detail.stage_results} />
          )}
          {tab === 'history' && (
            <div className="history-list">
              <div className="section-heading"><h2>Execution history</h2><span>Append-only</span></div>
              {detail.history.map((entry) => (
                <div key={entry.id}>
                  <span className="history-dot" />
                  <div><strong>{entry.event.replaceAll('_', ' ')}</strong><small>{entry.stage ?? 'engine'} · {entry.created_at}</small></div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
      <ProviderPicker />
    </aside>
  )
}

function TestEvidence({ results }: { results: StageResult[] }) {
  const result = results.find((item) => item.stage === 'tester')
  const output = result?.output as { passed?: number; failed?: number; coverage?: number } | undefined
  return (
    <div className="test-evidence">
      <div className="section-heading"><h2>Test result</h2><span>{result ? 'Recorded' : 'Pending'}</span></div>
      {result ? (
        <dl>
          <div><dt>Passed</dt><dd>{output?.passed ?? 0}</dd></div>
          <div><dt>Failed</dt><dd>{output?.failed ?? 0}</dd></div>
          <div><dt>Coverage</dt><dd>{Math.round((output?.coverage ?? 0) * 100)}%</dd></div>
        </dl>
      ) : <p className="empty-copy">Test evidence appears when the Tester commits its result.</p>}
    </div>
  )
}

function ProviderPicker() {
  return (
    <section className="provider-picker">
      <div><strong>Stage provider</strong><small>Tier eligibility enforced by engine</small></div>
      <select aria-label="Default stage provider" defaultValue="mock">
        <option value="mock">Mock · Heavy</option>
        <option disabled>Claude Code · Phase 7</option>
        <option disabled>Codex · Phase 7</option>
      </select>
    </section>
  )
}

function StateLabel({ state }: { state: string }) {
  const tone =
    state === 'DONE' || state.endsWith('ED')
      ? 'success'
      : state === 'FAILED' || state === 'REJECTED'
        ? 'danger'
        : state === 'AWAITING_APPROVAL'
          ? 'warning'
          : 'neutral'
  return <span className={`state-label state-label--${tone}`}><i />{state.replaceAll('_', ' ')}</span>
}

export default App
