const STEPS = [
  { key: 'overview',   label: 'Fetching stock overview' },
  { key: 'financials', label: 'Fetching historical financials' },
  { key: 'analysis',   label: 'Generating investment analysis' },
]

function stepIcon(status) {
  if (status === 'done')    return '✓'
  if (status === 'running') return '⟳'
  return '○'
}

export default function StepIndicator({ steps }) {
  return (
    <div className="step-indicator">
      {STEPS.map(({ key, label }) => (
        <div key={key} className={`step step--${steps[key]}`}>
          <span className="step-icon">{stepIcon(steps[key])}</span>
          <span>{label}</span>
        </div>
      ))}
    </div>
  )
}
