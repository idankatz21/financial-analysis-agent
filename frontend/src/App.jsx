import { useState } from 'react'
import TickerInput from './components/TickerInput'
import StepIndicator from './components/StepIndicator'
import MetricsPanel from './components/MetricsPanel'
import AnalysisPanel from './components/AnalysisPanel'

const INITIAL_STEPS = { overview: 'pending', financials: 'pending', analysis: 'pending' }

export default function App() {
  const [status, setStatus] = useState('idle')   // idle | loading | done | error
  const [steps, setSteps]   = useState(INITIAL_STEPS)
  const [result, setResult] = useState(null)
  const [error, setError]   = useState(null)

  const analyze = (ticker) => {
    setStatus('loading')
    setSteps(INITIAL_STEPS)
    setResult(null)
    setError(null)

    const source = new EventSource(`http://localhost:8000/analyze/${ticker}`)

    source.onmessage = (e) => {
      const event = JSON.parse(e.data)

      if (event.type === 'tool_call') {
        const stepKey = event.tool === 'get_stock_overview' ? 'overview' : 'financials'
        // Reset analysis to pending while a tool is actively running
        setSteps(s => ({ ...s, [stepKey]: 'running', analysis: 'pending' }))
      } else if (event.type === 'tool_result') {
        const stepKey = event.tool === 'get_stock_overview' ? 'overview' : 'financials'
        // After any tool completes, Claude is working on the next step
        setSteps(s => ({ ...s, [stepKey]: 'done', analysis: 'running' }))
      } else if (event.type === 'analysis') {
        setSteps(s => ({ ...s, analysis: 'done' }))
        setResult(event.data)
        setStatus('done')
        source.close()
      } else if (event.type === 'error') {
        setError(event.message)
        setStatus('error')
        source.close()
      }
    }

    source.onerror = () => {
      setError('Connection lost. Please try again.')
      setStatus('error')
      source.close()
    }
  }

  return (
    <div className="app">
      <h1>Financial Analysis Agent</h1>
      <TickerInput onSubmit={analyze} disabled={status === 'loading'} />
      {status === 'loading' && <StepIndicator steps={steps} />}
      {status === 'error' && (
        <div className="error-banner">{error}</div>
      )}
      {status === 'done' && result && (
        <>
          <MetricsPanel overview={result.overview} financials={result.financials} />
          <AnalysisPanel analysis={result.analysis} />
        </>
      )}
    </div>
  )
}
