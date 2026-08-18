import threading

from accumulator.event_buffer import EventBuffer


class TestEventBuffer:
    def test_add_and_len(self):
        buf = EventBuffer()
        assert len(buf) == 0
        buf.add({"symbol": "BTC"})
        assert len(buf) == 1

    def test_drain_returns_all_events(self):
        buf = EventBuffer()
        buf.add({"symbol": "BTC"})
        buf.add({"symbol": "ETH"})
        events = buf.drain()
        assert len(events) == 2
        assert events[0]["symbol"] == "BTC"
        assert events[1]["symbol"] == "ETH"

    def test_drain_clears_buffer(self):
        buf = EventBuffer()
        buf.add({"symbol": "BTC"})
        buf.drain()
        assert len(buf) == 0
        assert buf.drain() == []

    def test_drain_returns_copy(self):
        buf = EventBuffer()
        buf.add({"symbol": "BTC"})
        events = buf.drain()
        # Mutating the returned list should not affect the buffer
        events.append({"symbol": "X"})
        assert len(buf) == 0

    def test_add_after_drain(self):
        buf = EventBuffer()
        buf.add({"a": 1})
        buf.drain()
        buf.add({"b": 2})
        assert len(buf) == 1
        assert buf.drain() == [{"b": 2}]

    def test_thread_safety(self):
        buf = EventBuffer()
        errors = []

        def adder():
            try:
                for i in range(100):
                    buf.add({"id": i})
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=adder) for _ in range(4)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=5)

        assert not errors
        assert len(buf) == 400
