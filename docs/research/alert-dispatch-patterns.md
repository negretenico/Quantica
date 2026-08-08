# Alert Dispatch Patterns: match/case vs Decoupled Alternatives

**Date:** 2026-08-07
**Context:** `markettrade/run.py` uses structural pattern matching to dispatch on observer results (`NearLimitAlert`, `NearLimitCleared`, `ConcentrationAlert`, `ConcentrationCleared`). Each new observer type requires two new `case` branches. This document evaluates whether to keep the current approach or refactor.

---

## 1. Current Design

```
RiskObserverPipeline.check() -> list[Alert | Cleared | None]
```

`run.py` iterates the list and pattern-matches on concrete types:

```python
for result in risk_results:
    match result:
        case NearLimitAlert() as alert:     # store, counter, gauge, throttled log
        case NearLimitCleared() as cleared:  # discard from log-throttle set
        case ConcentrationAlert() as alert:  # store, counter, gauge=1
        case ConcentrationCleared():         # gauge=0
```

**Coupling point:** `run.py` imports every alert/cleared model and knows the side effects for each. Adding a third observer (e.g. `VolatilityObserver`) means adding `VolatilityAlert` and `VolatilityCleared` case branches, plus new metrics, plus new imports.

---

## 2. Patterns Evaluated

### 2a. Self-Handling Alerts (Strategy on the result object)

Each alert/cleared dataclass carries its own handler logic via a method:

```python
@dataclass(frozen=True)
class NearLimitAlert:
    symbol: str
    ratio: float
    ...

    def handle(self, ctx: AlertContext) -> None:
        ctx.store.write(self.to_dict())
        ctx.metrics.near_limit_alerts_total.labels(symbol=self.symbol).inc()
        ctx.metrics.near_limit_ratio.labels(symbol=self.symbol).set(self.ratio)
        if self.symbol not in ctx.logged:
            logger.warning("NEAR-LIMIT ...")
            ctx.logged.add(self.symbol)
```

Then `run.py` becomes:

```python
for result in risk_results:
    result.handle(ctx)
```

**Source:** Gang of Four *Strategy* pattern (Gamma et al., 1994, ch. 5). Also called *Command* when the object encapsulates both the action and its parameters.

**Pros:**
- Adding a new observer never touches `run.py`.
- Each alert type is self-contained: model + behavior in one place.
- Easy to test in isolation (pass a mock `AlertContext`).

**Cons:**
- Violates separation between `marketrisk` (a library) and `markettrade` (consumer). The alert models currently live in `marketrisk/risk/models.py`, which has no dependency on Prometheus, blob stores, or log-throttle sets. Adding `handle()` would either pull those dependencies into `marketrisk` or require `markettrade` to subclass/monkey-patch the models.
- Frozen dataclasses with behavior methods is a code smell -- these are value types.

**Verdict:** Wrong layering for our architecture. `marketrisk` is a pure library; side effects belong in `markettrade`.

---

### 2b. Handler Registry (Double Dispatch)

A registry maps alert types to handler callables. Handlers live in `markettrade`, models stay pure in `marketrisk`.

```python
# markettrade/alert_handlers.py
_registry: dict[type, Callable[[Any, AlertContext], None]] = {}

def handles(alert_type):
    def decorator(fn):
        _registry[alert_type] = fn
        return fn
    return decorator

def dispatch(result, ctx):
    handler = _registry.get(type(result))
    if handler:
        handler(result, ctx)

@handles(NearLimitAlert)
def on_near_limit(alert: NearLimitAlert, ctx: AlertContext) -> None:
    ctx.risk_alert_store.write(alert.to_dict())
    near_limit_alerts_total.labels(symbol=alert.symbol).inc()
    ...
```

Then `run.py` becomes:

```python
for result in risk_results:
    dispatch(result, ctx)
```

**Source:** This is a simplified *Mediator* (Gamma et al., 1994, ch. 5) combined with Python's `functools.singledispatch` concept. Django's signal dispatcher (`django.dispatch.Signal`) uses a similar registry-of-callables approach where `signal.connect(handler)` registers functions and `signal.send()` dispatches to all registered handlers (Django docs: "Signals > Defining and sending signals"). Celery uses a task registry keyed by name for a similar purpose.

PEP 443 (`functools.singledispatch`) is Python's stdlib mechanism for this pattern, dispatching on the type of the first argument. It could replace the manual registry:

```python
from functools import singledispatch

@singledispatch
def handle_risk_result(result, ctx):
    pass  # unknown types are no-ops

@handle_risk_result.register
def _(alert: NearLimitAlert, ctx: AlertContext):
    ...

@handle_risk_result.register
def _(cleared: NearLimitCleared, ctx: AlertContext):
    ...
```

**Pros:**
- Adding a new observer means adding a new handler function in `alert_handlers.py` -- no edit to `run.py`.
- Clean layering: models in `marketrisk`, side-effect handlers in `markettrade`.
- `singledispatch` is stdlib, zero dependencies, well-understood.
- Each handler is independently testable.

**Cons:**
- Harder to see all dispatch paths at a glance (must read the registry module).
- `singledispatch` does not natively support a second argument for dispatch -- the `ctx` is always passed positionally. This is fine for our case but means you can not dispatch on `(alert_type, context_type)` pairs.
- If a handler is not registered for a new alert type, it silently no-ops. The match/case approach would at least leave an obvious gap in the code during review.

---

### 2c. Observer-Owned Callbacks (on_fire / on_clear)

Each observer is constructed with callback functions for its fire/clear events:

```python
near_limit_observer = NearLimitObserver(
    threshold_pct=config.risk.NEAR_LIMIT_THRESHOLD_PCT,
    on_fire=lambda alert: ...,
    on_clear=lambda cleared: ...,
)
```

**Source:** Classic *Observer* pattern (Gamma et al., 1994, ch. 5). This is the event-listener style used by Node.js `EventEmitter`, Java's `ApplicationEventPublisher` (which this codebase already uses in `markettransformer`), and Python's `asyncio` callback protocols.

**Pros:**
- No dispatch loop at all -- the observer triggers its own side effects.
- Very explicit wiring at construction time.

**Cons:**
- Breaks the current `RiskObserverPipeline` contract where observers return values and the caller decides what to do. The pipeline would need to be restructured or eliminated.
- Callbacks defined as lambdas in `main()` would make the function even longer. Extracting them to named functions is equivalent to the registry pattern but with more boilerplate.
- Testing becomes harder: you must verify callback invocation rather than inspecting return values.
- The pipeline's sequential ordering guarantee (upstream state visible to downstream observers) is harder to reason about when side effects fire mid-pipeline.

**Verdict:** Worse ergonomics than the registry for our pipeline-based design.

---

### 2d. Event Bus / Mediator

A central event bus receives all results and fans them out to registered listeners:

```python
bus = EventBus()
bus.subscribe(NearLimitAlert, on_near_limit_alert)
bus.subscribe(NearLimitCleared, on_near_limit_cleared)

# In the pipeline:
for result in risk_results:
    bus.publish(result)
```

**Source:** *Mediator* pattern (Gamma et al., 1994). Enterprise Integration Patterns (Hohpe & Woolf, 2003) call this a *Message Router*. In Python, libraries like `blinker` and `pymitter` implement this. Django's `Signal` is essentially this with `connect()` / `send()`.

**Pros:**
- Maximum decoupling -- publishers and subscribers share no code.
- Multiple handlers per event type are trivial.

**Cons:**
- Overkill for 2 observers with 4 event types in a single-threaded hot path.
- Introduces a new abstraction (the bus) that adds indirection without proportional benefit.
- Debugging requires understanding the bus's subscription state.
- We already have RabbitMQ for inter-service eventing; an in-process bus for 4 event types is architectural overhead.

**Verdict:** Over-engineered for current scale.

---

### 2e. Keep match/case As-Is

PEP 636 (Structural Pattern Matching Tutorial) explicitly recommends match/case for dispatching on typed results: "Use match statements when you need to inspect the structure of data and act differently based on its shape." The pattern is idiomatic Python 3.10+ for exactly this scenario.

**Source:** PEP 634 (Specification), PEP 635 (Motivation and Rationale), PEP 636 (Tutorial). PEP 635 Section "Rejected Ideas" discusses why Python chose structural matching over visitor-style dispatch, arguing that match/case is more readable for a bounded set of types.

**Pros:**
- Maximally readable: all dispatch logic in one place, all side effects visible.
- No framework, no abstraction, no indirection.
- IDE support (jump-to-definition on each case branch) is excellent.
- Exhaustiveness is easy to audit visually.
- The hot path has zero overhead vs any dispatch mechanism.

**Cons:**
- Adding a new observer requires editing `run.py` (the original concern).
- As the observer count grows, the match block grows proportionally.

---

## 3. Scale Analysis

| Factor | Current state | Projection |
|--------|--------------|------------|
| Observer count | 2 (`NearLimit`, `Concentration`) | Likely 3-5 total (volatility, drawdown, correlation) |
| Case branches per observer | 2 (alert + cleared) | 2 per observer = 6-10 branches total |
| Frequency of new observer additions | ~1 per quarter | Low churn |
| Team size | Small | Match/case is the easiest to onboard |
| Hot path sensitivity | Every tick | All patterns have equivalent runtime cost |

At 2 observers (4 branches), the match block is 20 lines. At 5 observers it would be ~50 lines. Both are well within the range where match/case remains readable and maintainable.

---

## 4. The Hybrid Threshold

The right question is not "which pattern is best in the abstract" but "at what observer count does the match/case approach become painful enough to justify the indirection cost of a registry?"

Based on similar systems:
- **2-4 observers:** match/case is clearly better. The explicitness outweighs the coupling cost.
- **5-7 observers:** either approach works. The registry becomes attractive if observers are contributed by different developers or if the handler logic is substantial enough to warrant its own module.
- **8+ observers:** the registry (specifically `singledispatch`) becomes the clear winner. The match block would be 80+ lines of mixed concerns.

---

## 5. Recommendation

**Keep match/case now. Prepare for singledispatch later.**

Specifically:

1. **Keep the current match/case in `run.py`.** It is idiomatic, readable, and appropriate for 2 observers. The "coupling" concern is real but the cost of that coupling (editing `run.py` when adding an observer) is low and the benefit (all dispatch visible in one place) is high.

2. **Add a `# DISPATCH: add case branches here when adding new observers` comment** above the match block. This makes the edit point obvious and serves as a checklist item.

3. **When observer count reaches 5, extract to `singledispatch`.** At that point, create `markettrade/alert_handlers.py` with one `@singledispatch` function and per-type `@register` handlers. Each handler receives an `AlertContext` dataclass bundling the store, metrics, and log-throttle sets. The migration is mechanical:
   - Each `case` branch becomes a `@handle_risk_result.register` function.
   - `run.py` reduces to `for result in risk_results: handle_risk_result(result, ctx)`.
   - No changes to `marketrisk` models or observers.

4. **Do not use observer-owned callbacks or an event bus.** These add indirection without solving a problem we actually have. The pipeline's return-value-based contract is clean and testable.

### Why not refactor now?

Premature abstraction is a real cost on a small team. The registry pattern saves ~30 seconds per new observer addition (no need to open `run.py`) but costs permanent indirection in the codebase. At 2 observers, that trade is negative. At 5, it breaks even. Refactor when the pain is real, not when it is hypothetical.

---

## Sources

- **PEP 634** -- Structural Pattern Matching: Specification. https://peps.python.org/pep-0634/
- **PEP 635** -- Structural Pattern Matching: Motivation and Rationale. https://peps.python.org/pep-0635/
- **PEP 636** -- Structural Pattern Matching: Tutorial. https://peps.python.org/pep-0636/
- **PEP 443** -- Single-dispatch generic functions. https://peps.python.org/pep-0443/
- **Gamma, Helm, Johnson, Vlissides** -- *Design Patterns: Elements of Reusable Object-Oriented Software* (1994). Patterns: Strategy, Observer, Mediator, Command, Visitor.
- **Hohpe, Woolf** -- *Enterprise Integration Patterns* (2003). Message Router, Event-Driven Consumer.
- **Django Signals** -- https://docs.djangoproject.com/en/5.0/topics/signals/
- **Python `functools.singledispatch`** -- https://docs.python.org/3/library/functools.html#functools.singledispatch
