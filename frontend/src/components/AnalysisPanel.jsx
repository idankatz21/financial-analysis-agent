export default function AnalysisPanel({ analysis }) {
  return (
    <div className="analysis-panel">
      <div className="analysis-section analysis-section--bull">
        <h3>Bull Case</h3>
        <p>{analysis.bull_case}</p>
      </div>
      <div className="analysis-section analysis-section--bear">
        <h3>Bear Case</h3>
        <p>{analysis.bear_case}</p>
      </div>
      <div className="analysis-section analysis-section--risks">
        <h3>Key Risks</h3>
        <ul>
          {(analysis.key_risks ?? []).map((risk, i) => (
            <li key={i}>{risk}</li>
          ))}
        </ul>
      </div>
    </div>
  )
}
