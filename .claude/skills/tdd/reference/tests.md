# Good and Bad Tests

## Good Tests

**Integration-style**: Test through real interfaces, not mocks of internal parts.

**Java (JUnit 5)**
```java
@Test
void oddsSnapshotIsEnrichedWithGameId() {
    OddsSnapshot snapshot = oddsService.enrich(rawOdds);
    assertThat(snapshot.gameId()).isNotNull();
    assertThat(snapshot.homeOdds()).isPositive();
}
```

**Python (pytest)**
```python
def test_odds_snapshot_is_enriched_with_game_id():
    snapshot = odds_service.enrich(raw_odds)
    assert snapshot.game_id is not None
    assert snapshot.home_odds > 0
```

Characteristics:
- Tests behavior callers care about
- Uses public API only
- Survives internal refactors
- Describes WHAT, not HOW
- One logical assertion per test

## Bad Tests

**Implementation-detail tests**: Coupled to internal structure.

**Java**
```java
// BAD: verifies a collaborator was called, not what the system produced
@Test
void enrichCallsOddsClient() {
    oddsService.enrich(rawOdds);
    verify(oddsClient).fetch(any());
}
```

**Python**
```python
# BAD: same problem
def test_enrich_calls_odds_client():
    odds_service.enrich(raw_odds)
    mock_client.fetch.assert_called_once()
```

Red flags:
- Mocking internal collaborators
- Testing private methods
- Asserting on call counts or order
- Test breaks when refactoring without behavior change
- Test name describes HOW not WHAT

## Tautological Tests

Expected value restates the implementation — the test passes by construction and can never catch a bug.

**Java**
```java
// BAD: expected value computed the same way as the code
@Test
void calculatesTotalOdds() {
    List<Double> odds = List.of(1.5, 2.0, 1.8);
    double expected = odds.stream().mapToDouble(Double::doubleValue).sum();
    assertThat(oddsCalculator.total(odds)).isEqualTo(expected);
}

// GOOD: known literal from a worked example
@Test
void calculatesTotalOdds() {
    assertThat(oddsCalculator.total(List.of(1.5, 2.0, 1.8))).isEqualTo(5.3);
}
```

**Python**
```python
# BAD
def test_calculates_total_odds():
    odds = [1.5, 2.0, 1.8]
    expected = sum(odds)
    assert calculator.total(odds) == expected

# GOOD
def test_calculates_total_odds():
    assert calculator.total([1.5, 2.0, 1.8]) == 5.3
```
