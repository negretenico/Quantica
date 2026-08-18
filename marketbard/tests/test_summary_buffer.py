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
