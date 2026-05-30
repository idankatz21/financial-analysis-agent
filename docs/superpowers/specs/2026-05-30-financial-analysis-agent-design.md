# Financial Analysis Agent — Design Spec

**Date:** 2026-05-30  
**Status:** Approved

---

## Overview

A web app where a user enters a stock ticker symbol and receives a structured investment analysis. The backend runs a Claude tool-use agent loop that autonomously fetches real financial data and generates a bull case, bear case, and key risks. The frontend renders metrics as charts and KPI cards, and shows live progress via Server-Sent Events while the agent works.

---

## Architecture

```
React Frontend
     │  GET /analyze/{ticker}  (SSE stream)
     │◄─────────── SSE events ────────────────────
     ▼
FastAPI Backend
     │
     ├── SSE endpoint → spawns agent loop coroutine
     │
     └── Agent Loop (agent.py)
              │  Agentic loop: send messages → handle tool calls → repeat
              ▼
         Anthropic SDK (claude-sonnet-4-20250514, tool use)
              │
              ├── tool: get_stock_overview(ticker)
              └── tool: get_historical_financials(ticker, years)
                        │
                        └── yfinance
```

The agent loop runs a standard Claude tool-use conversation: send user message + tool schemas → if response contains tool calls, execute each tool, append results to messages, loop → when Claude returns plain text (the analysis), yield it as the final SSE event.

---

## Backend

### File Structure

```
backend/
├── main.py      # FastAPI app creation, router mounting, CORS
├── routes.py    # SSE endpoint: GET /analyze/{ticker}
├── agent.py     # Agent loop: Claude conversation with tool use
└── tools.py     # Tool implementations: yfinance fetches + metric calculation
```

### Tools (`tools.py`)

Two tools Claude can call:

**`get_stock_overview(ticker: str)`**
- Fetches via yfinance: company name, sector, P/E ratio (trailingPE), debt-to-equity (debtToEquity), market cap
- Validates the ticker by checking if yfinance returns a non-empty `info` dict
- Raises `ToolError("Ticker XYZ not found")` for unknown tickers
- Returns a typed dict

**`get_historical_financials(ticker: str, years: int = 5)`**
- Fetches annual financials via yfinance: revenue, net income, free cash flow for the last N years
- Returns structured time-series data (list of `{year, revenue, net_income, fcf}`)
- Raises `ToolError` if data is unavailable or insufficient

**`ToolError`** — a custom exception used to surface clean error messages through the SSE stream.

Tool schemas are defined as Anthropic-compatible JSON schema dicts, exported for use in `agent.py`.

### Agent Loop (`agent.py`)

```python
async def run_agent(ticker: str) -> AsyncGenerator[dict, None]:
    messages = [{"role": "user", "content": f"Analyze {ticker}..."}]
    accumulated = {}  # stores tool results keyed by tool name
    while True:
        response = await claude.messages.create(
            model="claude-sonnet-4-20250514",
            tools=TOOL_SCHEMAS,
            messages=messages,
        )
        if response.stop_reason == "tool_use":
            for tool_call in response.content:
                yield {"type": "tool_call", "tool": tool_call.name, "status": "running"}
                result = execute_tool(tool_call)   # calls tools.py; raises ToolError on failure
                accumulated[tool_call.name] = result
                yield {"type": "tool_result", "tool": tool_call.name, "status": "done"}
                messages = append_tool_result(messages, response, tool_call, result)
        else:
            # Bundle accumulated tool results with Claude's text analysis
            analysis_text = parse_claude_json(response)  # parses bull_case/bear_case/key_risks
            yield {"type": "analysis", "data": {
                "overview": accumulated.get("get_stock_overview"),
                "financials": accumulated.get("get_historical_financials"),
                "analysis": analysis_text,
            }}
            break
```

Errors from `execute_tool` (`ToolError`) are caught, yielded as `{"type": "error", "message": ...}`, and the loop exits.

### SSE Endpoint (`routes.py`)

- `GET /analyze/{ticker}` returns `text/event-stream`
- Each yielded dict from the agent loop is serialized as `data: <json>\n\n`
- FastAPI `StreamingResponse` with `media_type="text/event-stream"`

### Startup (`main.py`)

- Creates FastAPI app
- Mounts router from `routes.py`
- Configures CORS to allow the React dev server origin

---

## Frontend

### File Structure

```
frontend/src/
├── App.jsx                   # Root: SSE stream management, state, layout
└── components/
    ├── TickerInput.jsx        # Search bar + submit button (disabled during stream)
    ├── StepIndicator.jsx      # Live progress: 3 steps (overview, financials, analysis)
    ├── MetricsPanel.jsx       # KPI cards (P/E, D/E) + Recharts charts
    └── AnalysisPanel.jsx      # Bull case, bear case, key risks from Claude
```

### State Flow

`App.jsx` owns all state. On submit:
1. Opens `EventSource` to `/analyze/{ticker}`
2. Dispatches SSE events into local state:
   - `tool_call` / `tool_result` → updates step indicator state
   - `analysis` → sets metrics + analysis text, closes EventSource
   - `error` → sets error message, closes EventSource

### Charts (`MetricsPanel.jsx`)

| Metric | Visualization |
|---|---|
| P/E Ratio | KPI card (single value) |
| Debt-to-Equity | KPI card (single value) |
| Revenue (annual) | Bar chart (Recharts `BarChart`) |
| Free Cash Flow trend | Line chart (Recharts `LineChart`) |

### Analysis Display (`AnalysisPanel.jsx`)

Claude's final text response is structured JSON with three fields: `bull_case`, `bear_case`, `key_risks`. Each is rendered as a labeled section. Claude is prompted to return valid JSON.

### Loading State (`StepIndicator.jsx`)

Three named steps mapped to tool events:
1. **Fetching overview** — active when `get_stock_overview` tool_call received
2. **Fetching financials** — active when `get_historical_financials` tool_call received
3. **Generating analysis** — active after both tool results received, until `analysis` event

---

## Error Handling

### Backend
- Unknown ticker: `get_stock_overview` checks for empty yfinance `info` dict and raises `ToolError("Ticker XYZ not found")`; the agent loop catches it and yields an error event, stopping the loop
- yfinance network/data failure: caught in tool execution, yielded as error event
- Claude API failure: caught in agent loop, yielded as error event
- All errors stop the loop cleanly

### Frontend
- `{"type": "error"}` SSE event → renders inline error banner, replaces step indicator
- `EventSource.onerror` → renders "Connection lost" banner
- Ticker input disabled during active stream to prevent duplicate requests

---

## SSE Event Schema

```jsonc
// Tool invoked
{"type": "tool_call",   "tool": "get_stock_overview",        "status": "running"}

// Tool completed
{"type": "tool_result", "tool": "get_stock_overview",        "status": "done"}
{"type": "tool_call",   "tool": "get_historical_financials", "status": "running"}
{"type": "tool_result", "tool": "get_historical_financials", "status": "done"}

// Final analysis
{"type": "analysis", "data": {
  "overview":   { "company": "...", "sector": "...", "pe_ratio": 24.5, "debt_to_equity": 1.2, "market_cap": 2e12 },
  "financials": [{ "year": 2023, "revenue": 3.8e11, "net_income": 9.7e10, "fcf": 1.1e11 }, ...],
  "analysis":   { "bull_case": "...", "bear_case": "...", "key_risks": ["...", "..."] }
}}

// Error
{"type": "error", "message": "Ticker XXXX not found"}
```

---

## Claude Prompt Design

The initial user message instructs Claude to:
1. Call `get_stock_overview` to understand the company's current valuation and leverage
2. Call `get_historical_financials` to understand revenue growth and FCF trends
3. Return a JSON object with `bull_case` (string), `bear_case` (string), `key_risks` (array of strings)

Claude is instructed to return only valid JSON in its final message (no markdown fences).

---

## Environment & Setup

- `ANTHROPIC_API_KEY` set in environment (backend reads via `os.environ`)
- Backend: Python 3.11+, `fastapi`, `uvicorn`, `anthropic`, `yfinance`
- Frontend: Node 18+, React 18, `recharts`, Vite dev server
- README covers: architecture explanation, agent loop design, local run instructions

---

## Out of Scope

- Authentication / user accounts
- Multi-ticker comparison in a single session
- Persistent history / caching of results
- Deployment configuration (Docker, cloud)
