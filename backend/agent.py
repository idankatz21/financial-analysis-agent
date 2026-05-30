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
