"""Unit tests for shared risk computation utility."""

from mcp_server.utils import compute_symbol_exposure


SAMPLE_TRADES = [
    {
        "symbol": "BTCUSDT",
        "side": "BUY",
        "sized_quantity": 0.5,
        "risk_approved": True,
    },
    {
        "symbol": "BTCUSDT",
        "side": "BUY",
        "sized_quantity": 0.3,
        "risk_approved": True,
    },
    {
        "symbol": "BTCUSDT",
        "side": "SELL",
        "sized_quantity": 0.2,
        "risk_approved": True,
    },
    {
        "symbol": "BTCUSDT",
        "side": "BUY",
        "sized_quantity": 0.4,
        "risk_approved": False,  # rejected — should be excluded
    },
    {
        "symbol": "ETHUSDT",
        "side": "BUY",
        "sized_quantity": 1.0,
        "risk_approved": True,
    },
]


class TestComputeSymbolExposure:
    def test_computes_net_exposure_buy_minus_sell(self):
        result = compute_symbol_exposure(SAMPLE_TRADES, "BTCUSDT", 1.0)
        # 0.5 + 0.3 - 0.2 = 0.6
        assert result["current_exposure"] == 0.6
        assert result["headroom"] == 0.4
        assert result["max_exposure"] == 1.0

    def test_excludes_rejected_trades(self):
        result = compute_symbol_exposure(SAMPLE_TRADES, "BTCUSDT", 1.0)
        # The rejected BUY of 0.4 is excluded, so only 3 approved trades
        assert result["trade_count"] == 3

    def test_different_symbol(self):
        result = compute_symbol_exposure(SAMPLE_TRADES, "ETHUSDT", 2.0)
        assert result["current_exposure"] == 1.0
        assert result["headroom"] == 1.0
        assert result["trade_count"] == 1

    def test_unknown_symbol_returns_zero(self):
        result = compute_symbol_exposure(SAMPLE_TRADES, "XRPUSDT", 1.0)
        assert result["current_exposure"] == 0.0
        assert result["headroom"] == 1.0
        assert result["trade_count"] == 0

    def test_uses_quantity_fallback_when_no_sized_quantity(self):
        trades = [
            {
                "symbol": "DOTUSDT",
                "side": "BUY",
                "quantity": 5.0,
                "risk_approved": True,
            },
        ]
        result = compute_symbol_exposure(trades, "DOTUSDT", 10.0)
        assert result["current_exposure"] == 5.0

    def test_empty_trades_list(self):
        result = compute_symbol_exposure([], "BTCUSDT", 1.0)
        assert result["current_exposure"] == 0.0
        assert result["headroom"] == 1.0
        assert result["trade_count"] == 0

    def test_symbol_included_in_result(self):
        result = compute_symbol_exposure([], "BTCUSDT", 1.0)
        assert result["symbol"] == "BTCUSDT"
