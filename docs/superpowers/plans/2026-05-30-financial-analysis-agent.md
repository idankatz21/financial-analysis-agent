# Financial Analysis Agent — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a web app where a user enters a stock ticker and receives a Claude-powered investment analysis with real financial data, streamed live via SSE.

**Architecture:** FastAPI backend runs a Claude tool-use agent loop — Claude autonomously calls yfinance tools to gather data, then produces a structured JSON analysis. Progress is streamed to a React+Recharts dashboard via Server-Sent Events.

**Tech Stack:** Python 3.11, FastAPI, Anthropic SDK (`claude-sonnet-4-20250514`), yfinance, pandas, pytest, pytest-asyncio; React 18, Vite, Recharts

---

## File Map

**Backend (`backend/`)**
- `main.py` — FastAPI app, CORS middleware, router mount
- `routes.py` — `GET /analyze/{ticker}` SSE endpoint
- `agent.py` — async Claude tool-use agent loop
- `tools.py` — `ToolError`, `TOOL_SCHEMAS`, `get_stock_overview`, `get_historical_financials`, `execute_tool`
- `requirements.txt` — pinned Python dependencies
- `pytest.ini` — asyncio_mode = auto, testpaths = tests

**Tests (`backend/tests/`)**
- `__init__.py` — empty, makes tests a package
- `test_tools.py` — unit tests for tool functions (yfinance mocked)
- `test_agent.py` — unit tests for agent loop (Anthropic client mocked)

**Frontend (`frontend/`)**
- `index.html` — Vite HTML entry
- `vite.config.js` — Vite + React plugin
- `package.json` — dependencies
- `src/main.jsx` — React root mount
- `src/App.jsx` — root component, SSE stream state machine
- `src/index.css` — global styles
- `src/components/TickerInput.jsx` — ticker search form
- `src/components/StepIndicator.jsx` — live step progress display
- `src/components/MetricsPanel.jsx` — KPI cards + Recharts charts
- `src/components/AnalysisPanel.jsx` — bull/bear/risks text sections

**Root**
- `README.md`

---

## Task 1: Project Scaffold

**Files:**
- Create: `backend/requirements.txt`
- Create: `backend/pytest.ini`
- Create: `backend/tests/__init__.py`
- Create: `frontend/package.json`
- Create: `frontend/vite.config.js`
- Create: `frontend/index.html`
- Create: `frontend/src/main.jsx`

- [ ] **Step 1: Create backend directory and requirements**

```
backend/requirements.txt
```
```
fastapi==0.115.0
uvicorn[standard]==0.30.0
anthropic==0.40.0
yfinance==0.2.37
pandas==2.2.0
pytest==8.3.0
pytest-asyncio==0.23.0
httpx==0.27.0
```

- [ ] **Step 2: Create pytest.ini**

```
backend/pytest.ini
```
```ini
[pytest]
asyncio_mode = auto
testpaths = tests
```

- [ ] **Step 3: Create empty tests package**

Create `backend/tests/__init__.py` with empty content.

- [ ] **Step 4: Create frontend package.json**

```
frontend/package.json
```
```json
{
  "name": "financial-analysis-frontend",
  "private": true,
  "version": "0.0.0",
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "vite build",
    "preview": "vite preview"
  },
  "dependencies": {
    "react": "^18.2.0",
    "react-dom": "^18.2.0",
    "recharts": "^2.12.0"
  },
  "devDependencies": {
    "@vitejs/plugin-react": "^4.2.0",
    "vite": "^5.2.0"
  }
}
```

- [ ] **Step 5: Create vite.config.js**

```
frontend/vite.config.js
```
```js
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
})
```

- [ ] **Step 6: Create index.html**

```
frontend/index.html
```
```html
<!doctype html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>Financial Analysis Agent</title>
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.jsx"></script>
  </body>
</html>
```

- [ ] **Step 7: Create src/main.jsx**

```
frontend/src/main.jsx
```
```jsx
import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.jsx'

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <App />
  </StrictMode>,
)
```

- [ ] **Step 8: Install backend dependencies**

Run from `backend/`:
```
pip install -r requirements.txt
```
Expected: all packages install without error.

- [ ] **Step 9: Install frontend dependencies**

Run from `frontend/`:
```
npm install
```
Expected: `node_modules/` created, no errors.

- [ ] **Step 10: Commit**

```bash
git add backend/ frontend/
git commit -m "chore: project scaffold — backend requirements and frontend vite config"
```

---

## Task 2: Backend — tools.py (TDD)

**Files:**
- Create: `backend/tests/test_tools.py`
- Create: `backend/tools.py`

- [ ] **Step 1: Write the failing tests**

```
backend/tests/test_tools.py
```
```python
import pytest
from unittest.mock import patch
import pandas as pd
from tools import get_stock_overview, get_historical_financials, execute_tool, ToolError


def _make_financials_dataframes():
    dates = pd.to_datetime(["2023-09-30", "2022-09-30", "2021-09-30"])
    fin = pd.DataFrame({
        dates[0]: {"Total Revenue": 400e9, "Net Income": 100e9},
        dates[1]: {"Total Revenue": 380e9, "Net Income":  95e9},
        dates[2]: {"Total Revenue": 360e9, "Net Income":  90e9},
    })
    cf = pd.DataFrame({
        dates[0]: {"Free Cash Flow": 110e9},
        dates[1]: {"Free Cash Flow": 105e9},
        dates[2]: {"Free Cash Flow": 100e9},
    })
    return fin, cf


class TestGetStockOverview:
    def test_raises_tool_error_for_empty_info(self):
        with patch("tools.yf.Ticker") as MockTicker:
            MockTicker.return_value.info = {}
            with pytest.raises(ToolError, match="not found"):
                get_stock_overview("INVALID")

    def test_returns_expected_fields_for_valid_ticker(self):
        with patch("tools.yf.Ticker") as MockTicker:
            MockTicker.return_value.info = {
                "symbol": "AAPL",
                "longName": "Apple Inc.",
                "sector": "Technology",
                "trailingPE": 28.5,
                "debtToEquity": 150.0,
                "marketCap": 3_000_000_000_000,
            }
            result = get_stock_overview("AAPL")
        assert result == {
            "company": "Apple Inc.",
            "sector": "Technology",
            "pe_ratio": 28.5,
            "debt_to_equity": 150.0,
            "market_cap": 3_000_000_000_000,
        }

    def test_handles_missing_optional_fields(self):
        with patch("tools.yf.Ticker") as MockTicker:
            MockTicker.return_value.info = {"symbol": "XYZ", "longName": "XYZ Corp"}
            result = get_stock_overview("XYZ")
        assert result["pe_ratio"] is None
        assert result["debt_to_equity"] is None
        assert result["sector"] == "Unknown"


class TestGetHistoricalFinancials:
    def test_raises_tool_error_when_financials_empty(self):
        with patch("tools.yf.Ticker") as MockTicker:
            MockTicker.return_value.financials = pd.DataFrame()
            MockTicker.return_value.cashflow = pd.DataFrame()
            with pytest.raises(ToolError, match="No financial data"):
                get_historical_financials("INVALID")

    def test_returns_sorted_years_with_correct_values(self):
        fin, cf = _make_financials_dataframes()
        with patch("tools.yf.Ticker") as MockTicker:
            MockTicker.return_value.financials = fin
            MockTicker.return_value.cashflow = cf
            result = get_historical_financials("AAPL", years=3)
        assert len(result) == 3
        assert result[0]["year"] == 2021
        assert result[2]["year"] == 2023
        assert result[2]["revenue"] == 400e9
        assert result[2]["fcf"] == 110e9

    def test_respects_years_limit(self):
        fin, cf = _make_financials_dataframes()
        with patch("tools.yf.Ticker") as MockTicker:
            MockTicker.return_value.financials = fin
            MockTicker.return_value.cashflow = cf
            result = get_historical_financials("AAPL", years=1)
        assert len(result) == 1


class TestExecuteTool:
    def test_dispatches_get_stock_overview(self):
        with patch("tools.get_stock_overview", return_value={"company": "Apple"}) as mock:
            execute_tool("get_stock_overview", {"ticker": "AAPL"})
            mock.assert_called_once_with("AAPL")

    def test_dispatches_get_historical_financials_with_years(self):
        with patch("tools.get_historical_financials", return_value=[]) as mock:
            execute_tool("get_historical_financials", {"ticker": "AAPL", "years": 3})
            mock.assert_called_once_with("AAPL", 3)

    def test_dispatches_get_historical_financials_default_years(self):
        with patch("tools.get_historical_financials", return_value=[]) as mock:
            execute_tool("get_historical_financials", {"ticker": "AAPL"})
            mock.assert_called_once_with("AAPL", 5)

    def test_raises_tool_error_for_unknown_tool(self):
        with pytest.raises(ToolError, match="Unknown tool"):
            execute_tool("nonexistent_tool", {})
```

- [ ] **Step 2: Run tests to confirm they fail**

Run from `backend/`:
```
pytest tests/test_tools.py -v
```
Expected: `ImportError: No module named 'tools'` (or similar — no implementation yet).

- [ ] **Step 3: Write tools.py**

```
backend/tools.py
```
```python
from typing import Any
import yfinance as yf
import pandas as pd


class ToolError(Exception):
    pass


TOOL_SCHEMAS = [
    {
        "name": "get_stock_overview",
        "description": (
            "Fetch current stock overview: company name, sector, P/E ratio, "
            "debt-to-equity ratio, and market cap."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "ticker": {"type": "string", "description": "Stock ticker symbol, e.g. AAPL"},
            },
            "required": ["ticker"],
        },
    },
    {
        "name": "get_historical_financials",
        "description": (
            "Fetch annual revenue, net income, and free cash flow for the last N years."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "ticker": {"type": "string", "description": "Stock ticker symbol, e.g. AAPL"},
                "years": {
                    "type": "integer",
                    "description": "Number of years of history to fetch (default 5)",
                    "default": 5,
                },
            },
            "required": ["ticker"],
        },
    },
]


def get_stock_overview(ticker: str) -> dict:
    stock = yf.Ticker(ticker)
    info = stock.info
    if not info or "symbol" not in info:
        raise ToolError(f"Ticker '{ticker}' not found")
    return {
        "company": info.get("longName") or info.get("shortName", ticker),
        "sector": info.get("sector", "Unknown"),
        "pe_ratio": info.get("trailingPE"),
        "debt_to_equity": info.get("debtToEquity"),
        "market_cap": info.get("marketCap"),
    }


def get_historical_financials(ticker: str, years: int = 5) -> list[dict]:
    stock = yf.Ticker(ticker)
    financials = stock.financials
    cashflow = stock.cashflow

    if financials is None or financials.empty:
        raise ToolError(f"No financial data available for '{ticker}'")

    results = []
    for col in list(financials.columns)[:years]:
        year = col.year
        revenue = (
            float(financials.loc["Total Revenue", col])
            if "Total Revenue" in financials.index else None
        )
        net_income = (
            float(financials.loc["Net Income", col])
            if "Net Income" in financials.index else None
        )

        fcf = None
        if cashflow is not None and not cashflow.empty and col in cashflow.columns:
            if "Free Cash Flow" in cashflow.index:
                fcf = float(cashflow.loc["Free Cash Flow", col])
            elif (
                "Operating Cash Flow" in cashflow.index
                and "Capital Expenditure" in cashflow.index
            ):
                op_cf = float(cashflow.loc["Operating Cash Flow", col])
                capex = float(cashflow.loc["Capital Expenditure", col])
                fcf = op_cf + capex  # capex is negative in yfinance

        results.append({"year": year, "revenue": revenue, "net_income": net_income, "fcf": fcf})

    return sorted(results, key=lambda x: x["year"])


def execute_tool(name: str, input_data: dict) -> Any:
    if name == "get_stock_overview":
        return get_stock_overview(input_data["ticker"])
    if name == "get_historical_financials":
        return get_historical_financials(input_data["ticker"], input_data.get("years", 5))
    raise ToolError(f"Unknown tool: {name}")
```

- [ ] **Step 4: Run tests to confirm they pass**

Run from `backend/`:
```
pytest tests/test_tools.py -v
```
Expected output (all green):
```
tests/test_tools.py::TestGetStockOverview::test_raises_tool_error_for_empty_info PASSED
tests/test_tools.py::TestGetStockOverview::test_returns_expected_fields_for_valid_ticker PASSED
tests/test_tools.py::TestGetStockOverview::test_handles_missing_optional_fields PASSED
tests/test_tools.py::TestGetHistoricalFinancials::test_raises_tool_error_when_financials_empty PASSED
tests/test_tools.py::TestGetHistoricalFinancials::test_returns_sorted_years_with_correct_values PASSED
tests/test_tools.py::TestGetHistoricalFinancials::test_respects_years_limit PASSED
tests/test_tools.py::TestExecuteTool::test_dispatches_get_stock_overview PASSED
tests/test_tools.py::TestExecuteTool::test_dispatches_get_historical_financials_with_years PASSED
tests/test_tools.py::TestExecuteTool::test_dispatches_get_historical_financials_default_years PASSED
tests/test_tools.py::TestExecuteTool::test_raises_tool_error_for_unknown_tool PASSED
10 passed
```

- [ ] **Step 5: Commit**

```bash
git add backend/tools.py backend/tests/test_tools.py backend/tests/__init__.py
git commit -m "feat: backend tools.py — yfinance tool implementations with ToolError"
```

---

## Task 3: Backend — agent.py (TDD)

**Files:**
- Create: `backend/tests/test_agent.py`
- Create: `backend/agent.py`

- [ ] **Step 1: Write the failing tests**

```
backend/tests/test_agent.py
```
```python
from unittest.mock import AsyncMock, MagicMock, patch
from agent import run_agent
from tools import ToolError


def _tool_use_response(tool_name: str, tool_id: str, tool_input: dict):
    block = MagicMock()
    block.type = "tool_use"
    block.name = tool_name
    block.id = tool_id
    block.input = tool_input
    response = MagicMock()
    response.stop_reason = "tool_use"
    response.content = [block]
    return response


def _text_response(text: str):
    block = MagicMock()
    block.type = "text"
    block.text = text
    response = MagicMock()
    response.stop_reason = "end_turn"
    response.content = [block]
    return response


ANALYSIS_JSON = (
    '{"bull_case": "Strong growth", "bear_case": "High valuation",'
    ' "key_risks": ["rate risk", "competition"]}'
)

OVERVIEW_DATA = {
    "company": "Apple Inc.",
    "sector": "Technology",
    "pe_ratio": 28.5,
    "debt_to_equity": 150.0,
    "market_cap": 3e12,
}


async def test_agent_yields_tool_call_result_then_analysis():
    tool_resp = _tool_use_response("get_stock_overview", "id_1", {"ticker": "AAPL"})
    final_resp = _text_response(ANALYSIS_JSON)

    mock_client = MagicMock()
    mock_client.messages.create = AsyncMock(side_effect=[tool_resp, final_resp])

    with patch("agent.execute_tool", return_value=OVERVIEW_DATA):
        events = [e async for e in run_agent("AAPL", _client=mock_client)]

    assert events[0] == {"type": "tool_call", "tool": "get_stock_overview", "status": "running"}
    assert events[1] == {"type": "tool_result", "tool": "get_stock_overview", "status": "done"}
    assert events[2]["type"] == "analysis"
    assert events[2]["data"]["overview"] == OVERVIEW_DATA
    assert events[2]["data"]["analysis"]["bull_case"] == "Strong growth"
    assert events[2]["data"]["analysis"]["key_risks"] == ["rate risk", "competition"]


async def test_agent_yields_error_on_tool_error():
    tool_resp = _tool_use_response("get_stock_overview", "id_1", {"ticker": "BAD"})
    mock_client = MagicMock()
    mock_client.messages.create = AsyncMock(return_value=tool_resp)

    with patch("agent.execute_tool", side_effect=ToolError("Ticker 'BAD' not found")):
        events = [e async for e in run_agent("BAD", _client=mock_client)]

    error_events = [e for e in events if e["type"] == "error"]
    assert len(error_events) == 1
    assert "BAD" in error_events[0]["message"]


async def test_agent_yields_error_on_invalid_json_from_claude():
    final_resp = _text_response("not valid json {{{")
    mock_client = MagicMock()
    mock_client.messages.create = AsyncMock(return_value=final_resp)

    events = [e async for e in run_agent("AAPL", _client=mock_client)]

    assert events[-1]["type"] == "error"
    assert "parse" in events[-1]["message"].lower()


async def test_agent_accumulates_multiple_tool_results():
    overview_resp = _tool_use_response("get_stock_overview", "id_1", {"ticker": "AAPL"})
    financials_resp = _tool_use_response("get_historical_financials", "id_2", {"ticker": "AAPL"})
    # Claude calls both tools in separate turns
    final_resp = _text_response(ANALYSIS_JSON)

    mock_client = MagicMock()
    mock_client.messages.create = AsyncMock(
        side_effect=[overview_resp, financials_resp, final_resp]
    )

    financials_data = [{"year": 2023, "revenue": 400e9, "net_income": 100e9, "fcf": 110e9}]

    def fake_execute(name, _input):
        if name == "get_stock_overview":
            return OVERVIEW_DATA
        return financials_data

    with patch("agent.execute_tool", side_effect=fake_execute):
        events = [e async for e in run_agent("AAPL", _client=mock_client)]

    analysis_event = next(e for e in events if e["type"] == "analysis")
    assert analysis_event["data"]["overview"] == OVERVIEW_DATA
    assert analysis_event["data"]["financials"] == financials_data
```

- [ ] **Step 2: Run tests to confirm they fail**

Run from `backend/`:
```
pytest tests/test_agent.py -v
```
Expected: `ImportError: No module named 'agent'`

- [ ] **Step 3: Write agent.py**

```
backend/agent.py
```
```python
import json
from typing import AsyncGenerator, Optional
import anthropic
from tools import TOOL_SCHEMAS, execute_tool, ToolError

SYSTEM_PROMPT = """You are a financial analysis assistant. When given a stock ticker symbol:
1. Call get_stock_overview to get current valuation metrics (P/E ratio, debt-to-equity, market cap, sector)
2. Call get_historical_financials to get annual revenue, net income, and free cash flow trends
3. Based on the data you have gathered, return a JSON object with exactly these three fields:
   - bull_case: a paragraph describing the investment bull case
   - bear_case: a paragraph describing the investment bear case
   - key_risks: an array of 3-5 strings, each a specific risk factor

Return ONLY valid JSON in your final message. No markdown fences, no preamble, no explanation."""


async def run_agent(ticker: str, _client=None) -> AsyncGenerator[dict, None]:
    client = _client or anthropic.AsyncAnthropic()
    messages = [{"role": "user", "content": f"Please analyze the stock: {ticker.upper()}"}]
    accumulated = {}

    while True:
        try:
            response = await client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=2048,
                system=SYSTEM_PROMPT,
                tools=TOOL_SCHEMAS,
                messages=messages,
            )
        except anthropic.APIError as e:
            yield {"type": "error", "message": f"Claude API error: {e}"}
            return

        if response.stop_reason == "tool_use":
            tool_results_for_claude = []
            for block in response.content:
                if block.type != "tool_use":
                    continue
                yield {"type": "tool_call", "tool": block.name, "status": "running"}
                try:
                    result = execute_tool(block.name, block.input)
                    accumulated[block.name] = result
                    tool_results_for_claude.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": json.dumps(result),
                    })
                    yield {"type": "tool_result", "tool": block.name, "status": "done"}
                except ToolError as e:
                    yield {"type": "error", "message": str(e)}
                    return

            messages.append({"role": "assistant", "content": response.content})
            messages.append({"role": "user", "content": tool_results_for_claude})

        else:
            text = next(
                (block.text for block in response.content if hasattr(block, "text")), "{}"
            )
            try:
                analysis = json.loads(text)
            except json.JSONDecodeError:
                yield {"type": "error", "message": "Failed to parse structured analysis from Claude"}
                return

            yield {
                "type": "analysis",
                "data": {
                    "overview": accumulated.get("get_stock_overview"),
                    "financials": accumulated.get("get_historical_financials"),
                    "analysis": analysis,
                },
            }
            return
```

- [ ] **Step 4: Run tests to confirm they pass**

Run from `backend/`:
```
pytest tests/test_agent.py -v
```
Expected output:
```
tests/test_agent.py::test_agent_yields_tool_call_result_then_analysis PASSED
tests/test_agent.py::test_agent_yields_error_on_tool_error PASSED
tests/test_agent.py::test_agent_yields_error_on_invalid_json_from_claude PASSED
tests/test_agent.py::test_agent_accumulates_multiple_tool_results PASSED
4 passed
```

- [ ] **Step 5: Run full test suite**

Run from `backend/`:
```
pytest -v
```
Expected: 14 passed, 0 failed.

- [ ] **Step 6: Commit**

```bash
git add backend/agent.py backend/tests/test_agent.py
git commit -m "feat: backend agent.py — Claude tool-use agent loop with SSE event yielding"
```

---

## Task 4: Backend — routes.py + main.py

**Files:**
- Create: `backend/routes.py`
- Create: `backend/main.py`

- [ ] **Step 1: Write routes.py**

```
backend/routes.py
```
```python
import json
from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from agent import run_agent

router = APIRouter()


async def _event_stream(ticker: str):
    async for event in run_agent(ticker):
        yield f"data: {json.dumps(event)}\n\n"


@router.get("/analyze/{ticker}")
async def analyze(ticker: str):
    return StreamingResponse(
        _event_stream(ticker),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
```

- [ ] **Step 2: Write main.py**

```
backend/main.py
```
```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routes import router

app = FastAPI(title="Financial Analysis Agent")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["GET"],
    allow_headers=["*"],
)

app.include_router(router)
```

- [ ] **Step 3: Smoke-test the server**

Run from `backend/` (requires `ANTHROPIC_API_KEY` set):
```
uvicorn main:app --reload
```
Then in a separate terminal:
```
curl -N http://localhost:8000/analyze/AAPL
```
Expected: a stream of `data: {...}` lines starting with `tool_call` events. Stop with Ctrl+C.

- [ ] **Step 4: Commit**

```bash
git add backend/routes.py backend/main.py
git commit -m "feat: backend routes.py + main.py — SSE endpoint and FastAPI app"
```

---

## Task 5: Frontend — TickerInput.jsx

**Files:**
- Create: `frontend/src/components/TickerInput.jsx`

- [ ] **Step 1: Write the component**

```
frontend/src/components/TickerInput.jsx
```
```jsx
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
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/components/TickerInput.jsx
git commit -m "feat: TickerInput component — ticker search form with disabled state"
```

---

## Task 6: Frontend — StepIndicator.jsx

**Files:**
- Create: `frontend/src/components/StepIndicator.jsx`

- [ ] **Step 1: Write the component**

```
frontend/src/components/StepIndicator.jsx
```
```jsx
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
```

The `steps` prop shape: `{ overview: 'pending'|'running'|'done', financials: ..., analysis: ... }`.

- [ ] **Step 2: Commit**

```bash
git add frontend/src/components/StepIndicator.jsx
git commit -m "feat: StepIndicator component — live SSE progress display"
```

---

## Task 7: Frontend — MetricsPanel.jsx

**Files:**
- Create: `frontend/src/components/MetricsPanel.jsx`

- [ ] **Step 1: Write the component**

```
frontend/src/components/MetricsPanel.jsx
```
```jsx
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
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/components/MetricsPanel.jsx
git commit -m "feat: MetricsPanel component — KPI cards and Recharts bar/line charts"
```

---

## Task 8: Frontend — AnalysisPanel.jsx

**Files:**
- Create: `frontend/src/components/AnalysisPanel.jsx`

- [ ] **Step 1: Write the component**

```
frontend/src/components/AnalysisPanel.jsx
```
```jsx
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
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/components/AnalysisPanel.jsx
git commit -m "feat: AnalysisPanel component — bull/bear/risks sections"
```

---

## Task 9: Frontend — App.jsx + index.css

**Files:**
- Create: `frontend/src/App.jsx`
- Create: `frontend/src/index.css`

- [ ] **Step 1: Write App.jsx**

```
frontend/src/App.jsx
```
```jsx
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
        if (event.tool === 'get_stock_overview')
          setSteps(s => ({ ...s, overview: 'running' }))
        if (event.tool === 'get_historical_financials')
          setSteps(s => ({ ...s, financials: 'running' }))
      } else if (event.type === 'tool_result') {
        if (event.tool === 'get_stock_overview')
          setSteps(s => ({ ...s, overview: 'done' }))
        if (event.tool === 'get_historical_financials')
          setSteps(s => ({ ...s, financials: 'done', analysis: 'running' }))
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
```

- [ ] **Step 2: Write index.css**

```
frontend/src/index.css
```
```css
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

body {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  background: #f8fafc;
  color: #1e293b;
  min-height: 100vh;
}

.app {
  max-width: 900px;
  margin: 0 auto;
  padding: 2rem 1rem;
}

h1 {
  font-size: 1.75rem;
  font-weight: 700;
  margin-bottom: 1.5rem;
  color: #0f172a;
}

/* Ticker Input */
.ticker-form { display: flex; gap: 0.5rem; margin-bottom: 2rem; }

.ticker-form input {
  flex: 1;
  padding: 0.6rem 1rem;
  font-size: 1rem;
  border: 1px solid #cbd5e1;
  border-radius: 6px;
  outline: none;
  text-transform: uppercase;
}
.ticker-form input:focus { border-color: #4f46e5; box-shadow: 0 0 0 2px #e0e7ff; }
.ticker-form input:disabled { background: #f1f5f9; }

.ticker-form button {
  padding: 0.6rem 1.5rem;
  font-size: 1rem;
  background: #4f46e5;
  color: white;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  font-weight: 500;
  transition: background 0.15s;
}
.ticker-form button:hover:not(:disabled) { background: #4338ca; }
.ticker-form button:disabled { opacity: 0.5; cursor: not-allowed; }

/* Step Indicator */
.step-indicator {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
  padding: 1.25rem 1.5rem;
  background: white;
  border-radius: 8px;
  border: 1px solid #e2e8f0;
  margin-bottom: 2rem;
}
.step { display: flex; align-items: center; gap: 0.75rem; font-size: 0.95rem; color: #94a3b8; }
.step--running { color: #4f46e5; font-weight: 500; }
.step--done    { color: #10b981; }
.step-icon { font-size: 1.1rem; width: 1.25rem; text-align: center; }

/* Error */
.error-banner {
  padding: 0.85rem 1.25rem;
  background: #fef2f2;
  border: 1px solid #fecaca;
  border-radius: 8px;
  color: #dc2626;
  margin-bottom: 2rem;
}

/* Metrics Panel */
.metrics-panel {
  background: white;
  border-radius: 8px;
  border: 1px solid #e2e8f0;
  padding: 1.5rem;
  margin-bottom: 1.5rem;
}
.metrics-panel h2 { font-size: 1.2rem; margin-bottom: 1.25rem; }
.sector { color: #64748b; font-weight: 400; }

.kpi-row { display: flex; gap: 1rem; margin-bottom: 1.5rem; }
.kpi-card {
  flex: 1;
  padding: 1rem;
  background: #f8fafc;
  border-radius: 6px;
  border: 1px solid #e2e8f0;
}
.kpi-label {
  font-size: 0.75rem;
  color: #64748b;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  margin-bottom: 0.4rem;
}
.kpi-value { font-size: 1.5rem; font-weight: 700; color: #0f172a; }

.charts-row { display: grid; grid-template-columns: 1fr 1fr; gap: 1.5rem; }
.chart-container h3 { font-size: 0.85rem; color: #475569; margin-bottom: 0.75rem; font-weight: 500; }

/* Analysis Panel */
.analysis-panel { display: flex; flex-direction: column; gap: 1rem; }
.analysis-section {
  background: white;
  border-radius: 8px;
  border: 1px solid #e2e8f0;
  padding: 1.25rem 1.5rem;
}
.analysis-section h3 { font-size: 1rem; font-weight: 600; margin-bottom: 0.6rem; }
.analysis-section--bull h3  { color: #10b981; }
.analysis-section--bear h3  { color: #ef4444; }
.analysis-section--risks h3 { color: #f59e0b; }
.analysis-section p { font-size: 0.95rem; line-height: 1.65; color: #374151; }
.analysis-section ul { padding-left: 1.25rem; }
.analysis-section li { font-size: 0.95rem; line-height: 1.65; color: #374151; margin-bottom: 0.25rem; }
```

- [ ] **Step 3: Start the dev server and verify the app loads**

Run from `frontend/`:
```
npm run dev
```
Open `http://localhost:5173`. Expected: page loads with the title "Financial Analysis Agent" and the ticker input form visible. No console errors.

- [ ] **Step 4: Run a live end-to-end test**

Ensure the backend is running (`uvicorn main:app --reload` from `backend/` with `ANTHROPIC_API_KEY` set).

Enter `AAPL` in the input and click **Analyze**. Expected:
1. Input becomes disabled
2. Step indicator appears with "Fetching stock overview" highlighted
3. Steps advance as SSE events arrive
4. After ~10-30 seconds, MetricsPanel and AnalysisPanel render with real data

Enter `INVALID123` and click **Analyze**. Expected:
1. Step indicator briefly appears
2. Error banner renders with a message like "Ticker 'INVALID123' not found"

- [ ] **Step 5: Commit**

```bash
git add frontend/src/App.jsx frontend/src/index.css
git commit -m "feat: App.jsx + index.css — SSE state machine and dashboard styles"
```

---

## Task 10: README

**Files:**
- Create: `README.md`

- [ ] **Step 1: Write README.md**

```
README.md
```
```markdown
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
pytest -v
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
```

- [ ] **Step 2: Commit**

```bash
git add README.md
git commit -m "docs: README — architecture, agent loop design, and local run instructions"
```

---

## Self-Review

**Spec coverage check:**

| Requirement | Task |
|---|---|
| Python FastAPI backend | Tasks 1, 4 |
| React frontend | Tasks 1, 5–9 |
| yfinance for financial data | Task 2 |
| P/E ratio, revenue growth, D/E, FCF trend | Tasks 2, 7 |
| Claude `claude-sonnet-4-20250514` via Anthropic SDK | Task 3 |
| Bull case, bear case, key risks | Tasks 3, 8 |
| Recharts charts | Task 7 |
| Loading state showing current step | Tasks 6, 9 |
| SSE progress delivery | Tasks 3, 4, 9 |
| Error handling — yfinance / invalid ticker | Tasks 2, 3, 9 |
| Modular files (tools, agent, routes, components) | Tasks 2–9 |
| README with architecture + run instructions | Task 10 |

All requirements covered. ✓
