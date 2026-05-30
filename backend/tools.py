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
