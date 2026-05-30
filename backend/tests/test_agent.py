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


async def test_agent_yields_error_on_api_error():
    import anthropic as anthropic_lib
    mock_client = MagicMock()
    error = anthropic_lib.APIConnectionError(request=MagicMock())
    mock_client.messages.create = AsyncMock(side_effect=error)

    events = [e async for e in run_agent("AAPL", _client=mock_client)]

    assert len(events) == 1
    assert events[0]["type"] == "error"
    assert "Claude API error" in events[0]["message"]


async def test_agent_accumulates_multiple_tool_results():
    overview_resp = _tool_use_response("get_stock_overview", "id_1", {"ticker": "AAPL"})
    financials_resp = _tool_use_response("get_historical_financials", "id_2", {"ticker": "AAPL"})
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
