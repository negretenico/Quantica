from app.config import Config


def test_anomaly_threshold_default():
    assert Config.ANOMALY_THRESHOLD == 0.9


def test_anomaly_threshold_is_float():
    assert isinstance(Config.ANOMALY_THRESHOLD, float)
