# When to Mock

Mock at **system boundaries** only:

- External APIs (MLB Stats API, The Odds API)
- Kafka producers/consumers
- Time/randomness
- File system (sometimes)

Don't mock:
- Your own classes/modules
- Internal collaborators
- Anything you control

## Designing for Mockability

At system boundaries, design interfaces that are easy to mock.

**1. Use dependency injection**

Pass external dependencies in rather than creating them internally.

**Java**
```java
// Easy to mock — dependency injected
public class OddsService {
    private final OddsClient client;

    public OddsService(OddsClient client) {
        this.client = client;
    }
}

// Hard to mock — creates its own dependency
public class OddsService {
    public OddsSnapshot fetch(String gameId) {
        OddsClient client = new OddsClient(System.getenv("ODDS_API_KEY"));
        return client.fetch(gameId);
    }
}
```

**Python**
```python
# Easy to mock
class OddsService:
    def __init__(self, client: OddsClient):
        self.client = client

# Hard to mock
class OddsService:
    def fetch(self, game_id: str):
        client = OddsClient(os.environ["ODDS_API_KEY"])
        return client.fetch(game_id)
```

**2. Prefer specific interfaces over generic fetchers**

Create specific methods per external operation rather than one generic method with conditional logic.

**Java (Mockito)**
```java
// GOOD: each method is independently mockable
OddsClient mockClient = mock(OddsClient.class);
when(mockClient.fetchMoneyline("game-123")).thenReturn(snapshot);

// BAD: mock requires internal knowledge of how fetch() is called
when(mockClient.fetch("/sports/baseball_mlb/odds", Map.of("gameId", "game-123"))).thenReturn(...);
```

**Python (unittest.mock)**
```python
# GOOD
mock_client = MagicMock(spec=OddsClient)
mock_client.fetch_moneyline.return_value = snapshot

# BAD: mock must know the internal routing logic
mock_client.fetch.side_effect = lambda path, params: snapshot if params["gameId"] == "game-123" else None
```

The specific-interface approach means:
- Each mock returns one specific shape
- No conditional logic in test setup
- Easier to see which operations a test exercises
- Type safety per operation
