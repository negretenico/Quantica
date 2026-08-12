from functools import partial

from trade.models import SignalEvent
from trade.validation import (
    ValidationPipeline,
    ValidationResult,
    validate_price_sanity,
    validate_schema,
)


def _valid_payload(**overrides):
    base = {
        "symbol": "BTCUSDT",
        "type": "LARGE_TRADE",
        "cluster_id": 2,
        "anomaly_score": 0.9,
        "price": "42000.00",
        "quantity": "100.0",
    }
    base.update(overrides)
    return base


# --- Schema validator ---


class TestValidateSchema:
    def test_valid_payload_returns_event(self):
        result = validate_schema(_valid_payload())
        assert result.valid is True
        assert isinstance(result.event, SignalEvent)
        assert result.event.symbol == "BTCUSDT"

    def test_missing_required_field_rejects(self):
        payload = _valid_payload()
        del payload["symbol"]
        result = validate_schema(payload)
        assert result.valid is False
        assert result.reason == "symbol"

    def test_invalid_type_rejects(self):
        payload = _valid_payload(price="not_a_number")
        result = validate_schema(payload)
        assert result.valid is False
        assert result.reason is not None

    def test_empty_symbol_rejects(self):
        result = validate_schema(_valid_payload(symbol=""))
        assert result.valid is False


# --- Price sanity validator ---


class TestValidatePriceSanity:
    def test_in_range_passes(self):
        result = validate_price_sanity(
            _valid_payload(price="100.0"),
            enabled=True,
            min_price=0.0001,
            max_price=10000000.0,
        )
        assert result.valid is True

    def test_below_min_rejects(self):
        result = validate_price_sanity(
            _valid_payload(price="0.00001"),
            enabled=True,
            min_price=0.0001,
            max_price=10000000.0,
        )
        assert result.valid is False
        assert result.reason == "price_out_of_range"

    def test_above_max_rejects(self):
        result = validate_price_sanity(
            _valid_payload(price="99999999.0"),
            enabled=True,
            min_price=0.0001,
            max_price=10000000.0,
        )
        assert result.valid is False
        assert result.reason == "price_out_of_range"

    def test_disabled_always_passes(self):
        result = validate_price_sanity(
            _valid_payload(price="0.00001"),
            enabled=False,
            min_price=0.0001,
            max_price=10000000.0,
        )
        assert result.valid is True

    def test_missing_price_passes(self):
        payload = _valid_payload()
        del payload["price"]
        result = validate_price_sanity(
            payload,
            enabled=True,
            min_price=0.0001,
            max_price=10000000.0,
        )
        assert result.valid is True

    def test_non_numeric_price_passes(self):
        """Non-numeric price is not this validator's concern (schema catches it)."""
        result = validate_price_sanity(
            _valid_payload(price="abc"),
            enabled=True,
            min_price=0.0001,
            max_price=10000000.0,
        )
        assert result.valid is True


# --- Pipeline composition ---


class TestValidationPipeline:
    def test_all_pass_returns_valid_with_event(self):
        pipeline = ValidationPipeline([
            validate_schema,
            partial(
                validate_price_sanity,
                enabled=True,
                min_price=0.0001,
                max_price=10000000.0,
            ),
        ])
        result = pipeline.run(_valid_payload())
        assert result.valid is True
        assert isinstance(result.event, SignalEvent)
        assert result.event.symbol == "BTCUSDT"

    def test_stops_at_first_failure(self):
        """Schema fails first, so price sanity never runs."""
        calls = []

        def tracking_price_sanity(payload):
            calls.append("price_sanity")
            return ValidationResult(valid=True)

        pipeline = ValidationPipeline([
            validate_schema,
            tracking_price_sanity,
        ])
        payload = _valid_payload()
        del payload["symbol"]
        result = pipeline.run(payload)
        assert result.valid is False
        assert result.reason == "symbol"
        assert calls == []  # price sanity was never called

    def test_order_preserved_schema_before_price(self):
        """Payload that would fail both schema AND price: reason is schema."""
        payload = _valid_payload()
        del payload["symbol"]  # fails schema
        payload["price"] = "0.00001"  # would fail price sanity too

        pipeline = ValidationPipeline([
            validate_schema,
            partial(
                validate_price_sanity,
                enabled=True,
                min_price=0.0001,
                max_price=10000000.0,
            ),
        ])
        result = pipeline.run(payload)
        assert result.valid is False
        assert result.reason == "symbol"  # schema caught it first

    def test_second_validator_can_reject(self):
        pipeline = ValidationPipeline([
            validate_schema,
            partial(
                validate_price_sanity,
                enabled=True,
                min_price=1.0,
                max_price=100.0,
            ),
        ])
        result = pipeline.run(_valid_payload(price="42000.0"))
        assert result.valid is False
        assert result.reason == "price_out_of_range"

    def test_empty_pipeline_passes(self):
        pipeline = ValidationPipeline([])
        result = pipeline.run(_valid_payload())
        assert result.valid is True
        assert result.event is None
