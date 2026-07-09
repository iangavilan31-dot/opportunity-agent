import { useEffect, useRef, useState } from 'react'
import { Play, Square, ChevronDown, ChevronUp, Plus, X } from 'lucide-react'
import type { PipelineStatus } from '../types'
import { api } from '../api'

const DEFAULT_QUERIES = [
  'scheduling coordinator',
  'administrative coordinator',
  'operations assistant',
  'recruiting coordinator',
  'customer success coordinator',
  'CRM specialist',
  'intake coordinator',
  'data entry specialist',
  'office manager',
  'operations coordinator',
]

export default function Pipeline() {
  const [status, setStatus] = useState<PipelineStatus | null>(null)
  const [queries, setQueries] = useState<string[]>(DEFAULT_QUERIES)
  const [newQuery, setNewQuery] = useState('')
  const [showLog, setShowLog] = useState(true)
  const [polling, setPolling] = useState(false)
  const logRef = useRef<HTMLDivElement>(null)

  const fetchStatus = async () => {
    try {
      const s = await api.pipelineStatus()
      setStatus(s)
      return s
    } catch (e) {
      console.error(e)
      return null
    }
  }

  useEffect(() => {
    fetchStatus()
  }, [])

  // Auto-scroll log
  useEffect(() => {
    if (logRef.current) {
      logRef.current.scrollTop = logRef.current.scrollHeight
    }
  }, [status?.log])

  // Poll while running
  useEffect(() => {
    if (!polling) return
    const iv = setInterval(async () => {
      const s = await fetchStatus()
      if (!s || s.status !== 'running') {
        setPolling(false)
        clearInterval(iv)
      }
    }, 2000)
    return () => clearInterval(iv)
  }, [polling])

  const handleStart = async () => {
    try {
      await api.startPipeline(queries)
      setPolling(true)
      // Immediate poll
      setTimeout(fetchStatus, 500)
    } catch (e) {
      console.error(e)
    }
  }

  const addQuery = () => {
    const q = newQuery.trim().toLowerCase()
    if (q && !queries.includes(q)) {
      setQueries((prev) => [...prev, q])
    }
    setNewQuery('')
  }

  const isRunning = status?.status === 'running'
  const progress = status?.progress

  return (
    <div className="flex flex-col h-full overflow-y-auto">
      <div className="px-6 py-4 border-b border-border">
        <h1 className="text-primary font-semibold text-xl">Pipeline</h1>
        <p className="text-muted text-xs mt-0.5">
          Scrape → Score → Research → Generate emails → Queue for review
        </p>
      </div>

      <div className="p-6 flex flex-col gap-5">
        {/* Run Control */}
        <div className="bg-surface border border-border rounded-lg p-4 flex items-center justify-between">
          <div>
            <div className="text-primary text-md font-medium">
              {isRunning ? 'Pipeline Running…' : 'Pipeline Idle'}
            </div>
            {isRunning && progress && (
              <div className="text-muted text-xs mt-1 font-mono">
                {progress.scraped} scraped · {progress.scored} scored · {progress.passed} passed · {progress.researched} researched · {progress.emailed} queued
              </div>
            )}
          </div>

          <button
            onClick={handleStart}
            disabled={isRunning}
            className={`flex items-center gap-2 px-4 py-2 rounded text-sm font-medium transition-colors ${
              isRunning
                ? 'bg-s3 text-dim cursor-not-allowed'
                : 'bg-primary hover:bg-primary/90 text-bg'
            }`}
          >
            {isRunning ? <Square size={13} /> : <Play size={13} fill="currentColor" />}
            {isRunning ? 'Running…' : 'Run Pipeline'}
          </button>
        </div>

        {/* Progress bars */}
        {isRunning && progress && (
          <div className="bg-surface border border-border rounded-lg p-4 flex flex-col gap-3">
            {[
              { label: 'Scraped', value: progress.scraped, max: 100, color: '#4a4a52' },
              { label: 'Scored', value: progress.scored, max: progress.scraped || 1, color: '#6e6e78' },
              { label: 'Passed threshold', value: progress.passed, max: progress.scored || 1, color: '#9b9ba4' },
              { label: 'Researched', value: progress.researched, max: progress.passed || 1, color: '#c9c9cf' },
              { label: 'Emails generated', value: progress.emailed, max: progress.researched || 1, color: '#f5f5f6' },
            ].map(({ label, value, max, color }) => (
              <div key={label} className="flex items-center gap-3">
                <span className="text-xs text-muted w-36 shrink-0">{label}</span>
                <div className="flex-1 h-1 bg-s3 rounded-full overflow-hidden">
                  <div
                    className="h-full rounded-full transition-all duration-500"
                    style={{ width: `${Math.min(100, (value / max) * 100)}%`, background: color }}
                  />
                </div>
                <span className="text-xs text-dim font-mono w-8 text-right">{value}</span>
              </div>
            ))}
          </div>
        )}

        {/* Log */}
        {(status?.log?.length ?? 0) > 0 && (
          <div className="bg-surface border border-border rounded-lg overflow-hidden">
            <button
              onClick={() => setShowLog(!showLog)}
              className="w-full flex items-center justify-between px-4 py-2.5 text-muted hover:text-primary text-xs transition-colors"
            >
              <span>Run Log ({status!.log.length} lines)</span>
              {showLog ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
            </button>
            {showLog && (
              <div
                ref={logRef}
                className="border-t border-border px-4 py-3 max-h-64 overflow-y-auto"
              >
                {status!.log.map((line, i) => (
                  <div key={i} className="font-mono text-2xs text-muted leading-5">
                    {line}
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* Queries */}
        <div className="bg-surface border border-border rounded-lg p-4">
          <div className="text-xs text-muted mb-3">Job Search Queries ({queries.length})</div>
          <div className="flex flex-wrap gap-2 mb-3">
            {queries.map((q) => (
              <div
                key={q}
                className="flex items-center gap-1.5 px-2.5 py-1 bg-s2 border border-border rounded text-xs text-muted"
              >
                <span>{q}</span>
                <button
                  onClick={() => setQueries((prev) => prev.filter((x) => x !== q))}
                  className="text-dim hover:text-red transition-colors"
                >
                  <X size={10} />
                </button>
              </div>
            ))}
          </div>
          <div className="flex gap-2">
            <input
              value={newQuery}
              onChange={(e) => setNewQuery(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && addQuery()}
              placeholder="Add custom query…"
              className="flex-1 px-3 py-1.5 bg-s2 border border-border rounded text-sm text-primary placeholder-dim focus:border-accent/50"
            />
            <button
              onClick={addQuery}
              className="px-3 py-1.5 text-xs text-muted hover:text-primary border border-border rounded transition-colors"
            >
              <Plus size={12} />
            </button>
          </div>
        </div>

        {/* Config Status */}
        <div className="bg-surface border border-border rounded-lg p-4">
          <div className="text-xs text-muted mb-3">Configuration</div>
          <div className="flex flex-col gap-2">
            {[
              { label: 'ANTHROPIC_API_KEY', required: true },
              { label: 'RAPIDAPI_KEY (JSearch)', required: false },
              { label: 'HUNTER_API_KEY (contacts)', required: false },
            ].map(({ label, required }) => (
              <div key={label} className="flex items-center justify-between">
                <span className="text-xs text-muted font-mono">{label}</span>
                <span className={`text-2xs ${required ? 'text-yellow' : 'text-dim'}`}>
                  {required ? 'Required' : 'Optional'}
                </span>
              </div>
            ))}
          </div>
          <div className="text-2xs text-dim mt-3">
            Configure in <code className="font-mono">backend/.env</code>
          </div>
        </div>
      </div>
    </div>
  )
}
