import {
  BarChart, Bar, LineChart, Line,
  XAxis, YAxis, Tooltip, ResponsiveContainer,
} from 'recharts'

function fmt(n) {
  if (n == null) return 'N/A'
  const abs = Math.abs(n)
  if (abs >= 1e12) return `$${(n / 1e12).toFixed(2)}T`
  if (abs >= 1e9)  return `$${(n / 1e9).toFixed(2)}B`
  if (abs >= 1e6)  return `$${(n / 1e6).toFixed(2)}M`
  return `$${n.toFixed(2)}`
}

function KpiCard({ label, value }) {
  return (
    <div className="kpi-card">
      <div className="kpi-label">{label}</div>
      <div className="kpi-value">{value ?? 'N/A'}</div>
    </div>
  )
}

export default function MetricsPanel({ overview, financials }) {
  const revenueData = (financials ?? []).map(f => ({
    year: f.year,
    revenue: f.revenue != null ? +(f.revenue / 1e9).toFixed(2) : null,
  }))

  const fcfData = (financials ?? [])
    .filter(f => f.fcf != null)
    .map(f => ({ year: f.year, fcf: +(f.fcf / 1e9).toFixed(2) }))

  return (
    <div className="metrics-panel">
      <h2>
        {overview?.company}{' '}
        <span className="sector">({overview?.sector})</span>
      </h2>

      <div className="kpi-row">
        <KpiCard label="P/E Ratio"     value={overview?.pe_ratio?.toFixed(2)} />
        <KpiCard label="Debt / Equity" value={overview?.debt_to_equity?.toFixed(2)} />
        <KpiCard label="Market Cap"    value={fmt(overview?.market_cap)} />
      </div>

      <div className="charts-row">
        <div className="chart-container">
          <h3>Annual Revenue (USD Billions)</h3>
          <ResponsiveContainer width="100%" height={200}>
            <BarChart data={revenueData}>
              <XAxis dataKey="year" />
              <YAxis tickFormatter={v => `$${v}B`} width={60} />
              <Tooltip formatter={v => [`$${v}B`, 'Revenue']} />
              <Bar dataKey="revenue" fill="#4f46e5" radius={[3, 3, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>

        <div className="chart-container">
          <h3>Free Cash Flow Trend (USD Billions)</h3>
          <ResponsiveContainer width="100%" height={200}>
            <LineChart data={fcfData}>
              <XAxis dataKey="year" />
              <YAxis tickFormatter={v => `$${v}B`} width={60} />
              <Tooltip formatter={v => [`$${v}B`, 'FCF']} />
              <Line
                type="monotone"
                dataKey="fcf"
                stroke="#10b981"
                strokeWidth={2}
                dot={{ r: 4 }}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>
    </div>
  )
}
