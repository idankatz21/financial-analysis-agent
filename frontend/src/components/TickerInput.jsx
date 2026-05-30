import { useState } from 'react'

export default function TickerInput({ onSubmit, disabled }) {
  const [ticker, setTicker] = useState('')

  const handleSubmit = (e) => {
    e.preventDefault()
    const t = ticker.trim().toUpperCase()
    if (t) onSubmit(t)
  }

  return (
    <form className="ticker-form" onSubmit={handleSubmit}>
      <input
        type="text"
        value={ticker}
        onChange={e => setTicker(e.target.value)}
        placeholder="Enter ticker symbol (e.g. AAPL)"
        disabled={disabled}
        autoFocus
      />
      <button type="submit" disabled={disabled || !ticker.trim()}>
        Analyze
      </button>
    </form>
  )
}
