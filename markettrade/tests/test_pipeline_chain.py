from trade.pipeline.chain import Pipeline
from trade.pipeline.context import PipelineContext


class _PassStep:
    def __init__(self, name, log):
        self.name = name
        self._log = log

    def execute(self, ctx):
        self._log.append(self.name)
        return True


class _HaltStep:
    def __init__(self, name, log):
        self.name = name
        self._log = log

    def execute(self, ctx):
        self._log.append(self.name)
        return False


class TestPipeline:
    def test_all_steps_execute_in_order(self):
        log = []
        pipeline = Pipeline([
            _PassStep("a", log),
            _PassStep("b", log),
            _PassStep("c", log),
        ])
        pipeline.execute(PipelineContext(payload={}))
        assert log == ["a", "b", "c"]

    def test_halting_step_stops_chain(self):
        log = []
        pipeline = Pipeline([
            _PassStep("a", log),
            _HaltStep("b", log),
            _PassStep("c", log),
        ])
        pipeline.execute(PipelineContext(payload={}))
        assert log == ["a", "b"]

    def test_first_step_halts(self):
        log = []
        pipeline = Pipeline([
            _HaltStep("a", log),
            _PassStep("b", log),
        ])
        pipeline.execute(PipelineContext(payload={}))
        assert log == ["a"]

    def test_empty_pipeline(self):
        pipeline = Pipeline([])
        pipeline.execute(PipelineContext(payload={}))

    def test_context_is_shared_across_steps(self):
        class SetEventStep:
            def execute(self, ctx):
                ctx.event = "test_event"
                return True

        class ReadEventStep:
            def __init__(self):
                self.seen_event = None

            def execute(self, ctx):
                self.seen_event = ctx.event
                return True

        reader = ReadEventStep()
        pipeline = Pipeline([SetEventStep(), reader])
        pipeline.execute(PipelineContext(payload={}))
        assert reader.seen_event == "test_event"
