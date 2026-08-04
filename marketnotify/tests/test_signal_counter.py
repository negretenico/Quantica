from handlers.signal_counter import SignalCounter, SignalSnapshot


class TestSignalCounter:
    def test_initial_snapshot_is_zero(self):
        counter = SignalCounter()
        snap = counter.snapshot_and_reset()
        assert snap == SignalSnapshot(received=0, duplicates=0, counted=0)

    def test_record_received(self):
        counter = SignalCounter()
        counter.record_received()
        counter.record_received()
        snap = counter.snapshot_and_reset()
        assert snap.received == 2

    def test_record_duplicate(self):
        counter = SignalCounter()
        counter.record_received()
        counter.record_duplicate()
        snap = counter.snapshot_and_reset()
        assert snap.received == 1
        assert snap.duplicates == 1
        assert snap.counted == 0

    def test_record_counted(self):
        counter = SignalCounter()
        counter.record_received()
        counter.record_counted()
        snap = counter.snapshot_and_reset()
        assert snap.received == 1
        assert snap.counted == 1

    def test_snapshot_resets_all(self):
        counter = SignalCounter()
        counter.record_received()
        counter.record_received()
        counter.record_duplicate()
        counter.record_counted()
        first = counter.snapshot_and_reset()
        assert first == SignalSnapshot(received=2, duplicates=1, counted=1)

        second = counter.snapshot_and_reset()
        assert second == SignalSnapshot(received=0, duplicates=0, counted=0)

    def test_full_flow(self):
        """Simulates the handle_signal callback pattern."""
        counter = SignalCounter()

        # 3 events received, 1 duplicate, 2 counted
        for _ in range(3):
            counter.record_received()
        counter.record_duplicate()
        counter.record_counted()
        counter.record_counted()

        snap = counter.snapshot_and_reset()
        assert snap.received == 3
        assert snap.duplicates == 1
        assert snap.counted == 2
