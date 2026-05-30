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
