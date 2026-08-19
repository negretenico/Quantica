import threading

from accumulator.summary_buffer import SummaryBuffer


class TestSummaryBuffer:
    def test_add_and_len(self):
        buf = SummaryBuffer(maxlen=10)
        assert len(buf) == 0
        buf.add({"window_start": "09:30"})
        assert len(buf) == 1

    def test_drain_returns_all_and_clears(self):
        buf = SummaryBuffer(maxlen=10)
        buf.add({"window_start": "09:30"})
        buf.add({"window_start": "09:40"})
        items = buf.drain()
        assert len(items) == 2
        assert len(buf) == 0

    def test_maxlen_evicts_oldest(self):
        buf = SummaryBuffer(maxlen=3)
        buf.add({"id": 1})
        buf.add({"id": 2})
        buf.add({"id": 3})
        buf.add({"id": 4})
        items = buf.drain()
        assert len(items) == 3
        assert items[0]["id"] == 2  # oldest (id=1) was evicted

    def test_drain_returns_list_not_deque(self):
        buf = SummaryBuffer(maxlen=5)
        buf.add({"x": 1})
        result = buf.drain()
        assert isinstance(result, list)

    def test_empty_drain(self):
        buf = SummaryBuffer(maxlen=5)
        assert buf.drain() == []

    def test_thread_safety(self):
        buf = SummaryBuffer(maxlen=500)
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
        buf = SummaryBuffer(maxlen=500)
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

        drained.append(buf.drain())

        assert not errors
        total = sum(len(batch) for batch in drained)
        assert total == 200

    def test_eviction_preserves_newest(self):
        buf = SummaryBuffer(maxlen=2)
        buf.add({"id": "a"})
        buf.add({"id": "b"})
        buf.add({"id": "c"})
        items = buf.drain()
        assert [s["id"] for s in items] == ["b", "c"]

    def test_add_after_drain(self):
        buf = SummaryBuffer(maxlen=10)
        buf.add({"x": 1})
        buf.drain()
        buf.add({"x": 2})
        assert len(buf) == 1
        assert buf.drain() == [{"x": 2}]
