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

    def test_concurrent_add_and_drain(self):
        buf = EventBuffer()
        drained: list[list] = []
        errors = []

        def adder():
            try:
                for i in range(200):
                    buf.add({"id": i})
            except Exception as e:
                errors.append(e)

        def drainer():
            try:
                for _ in range(20):
                    drained.append(buf.drain())
            except Exception as e:
                errors.append(e)

        t1 = threading.Thread(target=adder)
        t2 = threading.Thread(target=drainer)
        t1.start()
        t2.start()
        t1.join(timeout=5)
        t2.join(timeout=5)

        # Final drain to catch any remaining
        drained.append(buf.drain())

        assert not errors
        total = sum(len(batch) for batch in drained)
        assert total == 200

    def test_preserves_insertion_order(self):
        buf = EventBuffer()
        for i in range(50):
            buf.add({"seq": i})
        events = buf.drain()
        assert [e["seq"] for e in events] == list(range(50))
