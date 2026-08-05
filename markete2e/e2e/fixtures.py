import time


def _now_ms() -> int:
    return int(time.time() * 1000)


def valid_trade_event(
    symbol: str = "BTCUSDT",
    price: str = "108255.20",
    quantity: str = "0.010",
    is_buyer_market_maker: bool = True,
) -> dict:
    """Standard valid BinanceStreamResponse event."""
    ts = _now_ms()
    return {
        "e": "trade",
        "E": ts,
        "T": ts,
        "s": symbol,
        "t": 387235071,
        "p": price,
        "q": quantity,
        "X": "MARKET",
        "m": is_buyer_market_maker,
    }


def malformed_event_missing_fields() -> dict:
    """Event missing required fields (s, p, q absent)."""
    ts = _now_ms()
    return {
        "e": "trade",
        "E": ts,
        "T": ts,
    }


def malformed_event_bad_types() -> dict:
    """Event with wrong types: p as int, E as string."""
    return {
        "e": "trade",
        "E": "not_a_number",
        "T": "not_a_number",
        "s": "BTCUSDT",
        "t": "not_a_number",
        "p": 108255,
        "q": 0.010,
        "X": "MARKET",
        "m": "true",
    }


def zero_price_event(symbol: str = "BTCUSDT") -> dict:
    """Edge case: price is zero."""
    ts = _now_ms()
    return {
        "e": "trade",
        "E": ts,
        "T": ts,
        "s": symbol,
        "t": 387235072,
        "p": "0.00",
        "q": "1.000",
        "X": "MARKET",
        "m": True,
    }


def negative_price_event(symbol: str = "BTCUSDT") -> dict:
    """Edge case: negative price (invalid but parseable)."""
    ts = _now_ms()
    return {
        "e": "trade",
        "E": ts,
        "T": ts,
        "s": symbol,
        "t": 387235073,
        "p": "-1.00",
        "q": "1.000",
        "X": "MARKET",
        "m": True,
    }


def extreme_price_event(symbol: str = "BTCUSDT") -> dict:
    """Edge case: extremely large price."""
    ts = _now_ms()
    return {
        "e": "trade",
        "E": ts,
        "T": ts,
        "s": symbol,
        "t": 387235074,
        "p": "9999999999.99",
        "q": "1.000",
        "X": "MARKET",
        "m": True,
    }


def tiny_quantity_event(symbol: str = "BTCUSDT") -> dict:
    """Edge case: dust trade with extremely small quantity."""
    ts = _now_ms()
    return {
        "e": "trade",
        "E": ts,
        "T": ts,
        "s": symbol,
        "t": 387235075,
        "p": "108255.20",
        "q": "0.00000001",
        "X": "MARKET",
        "m": True,
    }
