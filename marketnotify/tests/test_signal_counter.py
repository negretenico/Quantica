from handlers.signal_counter import SignalCounter


class TestSignalCounter:
    def test_initial_count_is_zero(self):
        counter = SignalCounter()
        assert counter.count == 0

    def test_increment(self):
        counter = SignalCounter()
        counter.increment()
        counter.increment()
        assert counter.count == 2

    def test_get_and_reset(self):
        counter = SignalCounter()
        counter.increment()
        counter.increment()
        counter.increment()
        result = counter.get_and_reset()
        assert result == 3
        assert counter.count == 0

    def test_get_and_reset_when_empty(self):
        counter = SignalCounter()
        result = counter.get_and_reset()
        assert result == 0
