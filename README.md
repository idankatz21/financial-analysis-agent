# Financial Analysis Agent

A full-stack web app that uses Claude as a tool-use agent to autonomously fetch real financial data and generate structured investment analyses.

## Architecture

```
React Frontend (Vite + Recharts)
        │
        │  GET /analyze/{ticker}  — Server-Sent Events stream
        │
FastAPI Backend
        │
        └─── Agent Loop (agent.py)
                │
                │  Claude claude-sonnet-4-20250514
                │  (tool-use API)
                │
                ├── tool: get_stock_overview(ticker)
                │         └── yfinance → P/E, D/E, market cap, sector
                │
                └── tool: get_historical_financials(ticker, years)
                          └── yfinance → annual revenue, net income, FCF
```

## Agent Loop Design

The backend does not run a fixed pipeline. It runs a true Claude tool-use agent loop:

1. The user submits a ticker; the frontend opens a Server-Sent Events connection to `/analyze/{ticker}`
2. The backend sends Claude a message asking it to analyze the ticker, along with two tool schemas
3. Claude autonomously decides which tools to call and in what order
4. Each tool call is executed on the backend using yfinance, and the result is fed back to Claude as a tool result message
5. Claude loops until it has gathered enough data, then returns a structured JSON object with `bull_case`, `bear_case`, and `key_risks`
6. The backend bundles the accumulated tool results (metrics data for charts) with Claude's analysis text and emits a final `analysis` SSE event

Progress events are streamed in real time: the frontend receives `tool_call` and `tool_result` events as each step happens, driving the step indicator in the UI.

## Running Locally

### Prerequisites

- Python 3.11+
- Node 18+
- An Anthropic API key

### Backend

```bash
cd backend
pip install -r requirements.txt

# Set your Anthropic API key:
# macOS/Linux:
export ANTHROPIC_API_KEY=sk-ant-...
# Windows (PowerShell):
$env:ANTHROPIC_API_KEY = "sk-ant-..."

uvicorn main:app --reload
# Server starts at http://localhost:8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev
# Opens at http://localhost:5173
```

Enter a ticker symbol (e.g. `AAPL`, `MSFT`, `TSLA`) and click **Analyze**.

### Tests

```bash
cd backend
python -m pytest -v
```

## Project Structure

```
backend/
├── main.py          FastAPI app + CORS
├── routes.py        SSE endpoint: GET /analyze/{ticker}
├── agent.py         Claude tool-use agent loop
├── tools.py         yfinance tool implementations + ToolError
├── requirements.txt
└── tests/
    ├── test_tools.py
    └── test_agent.py

frontend/
├── index.html
└── src/
    ├── main.jsx
    ├── App.jsx                  SSE stream state machine
    ├── index.css
    └── components/
        ├── TickerInput.jsx      Ticker search form
        ├── StepIndicator.jsx    Live step progress display
        ├── MetricsPanel.jsx     KPI cards + Recharts charts
        └── AnalysisPanel.jsx    Bull case / bear case / key risks
```

## Error Handling

- **Unknown ticker**: `get_stock_overview` detects an empty yfinance response and raises a `ToolError`. The agent loop catches it, emits an `{"type": "error"}` SSE event, and stops. The frontend renders an inline error banner.
- **yfinance failure**: Same path — `ToolError` → error SSE event → error banner.
- **Claude API failure**: Caught in the agent loop, yielded as an error event.
- **Connection lost**: The frontend's `EventSource.onerror` handler renders a "Connection lost" banner.
