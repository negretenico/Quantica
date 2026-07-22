# Research: Binance WebSocket Multi-Symbol Streams

**Date:** 2026-07-21
**Scope:** Binance USDⓈ-M Futures + Spot — multi-symbol WebSocket subscription options
**Primary sources:** Binance Developer Docs (fetched directly)

---

## Summary

Binance supports multiple symbols on a **single WebSocket connection** via two mechanisms:

1. **Combined stream URL** — list streams in the URL path or query string at connection time
2. **Dynamic subscribe/unsubscribe** — connect once to a generic endpoint, then send JSON messages to add/remove streams at runtime

Quantica currently uses neither. It opens one hardcoded URL (`btcusdt@trade`) and cannot change symbols without a restart. This is the root cause the branch `63-feature-make-marketlistener-stateless-symbol-from-symbol-env-var-kafka-records-keyed-by-symbol` was opened to address.

---

## Findings

### 1. Futures — Combined Stream in URL Path (WS Mode)

**Source:** https://developers.binance.com/docs/derivatives/usds-margined-futures/websocket-market-streams/Connect

Streams can be listed directly in the URL path, separated by `/`:

```
wss://fstream.binance.com/public/ws/bnbusdt@depth/ethusdt@depth/btcusdt@trade
```

The general pattern:

```
wss://fstream.binance.com/{endpoint}/ws/{stream1}/{stream2}/...
```

Where `{endpoint}` is one of:
- `public` — high-frequency public data (recommended for market streams)
- `market` — regular market data
- `private` — user data streams

For `@trade` streams specifically: **yes, multi-symbol works the same way.**

```
wss://fstream.binance.com/public/ws/btcusdt@trade/ethusdt@trade/bnbusdt@trade
```

---

### 2. Futures — Combined Stream via Query String (Stream Mode)

**Source:** https://developers.binance.com/docs/derivatives/usds-margined-futures/websocket-market-streams/Connect

```
wss://fstream.binance.com/market/stream?streams=bnbusdt@aggTrade/btcusdt@markPrice
```

Combined stream responses are **wrapped** in an envelope:

```json
{
  "stream": "btcusdt@trade",
  "data": { ...raw payload... }
}
```

This means the `BinanceStreamResponse` parsing in Quantica would need to handle this wrapper if using stream mode (vs. WS mode, which does not wrap by default).

---

### 3. Dynamic Subscribe/Unsubscribe (Spot — confirmed; Futures likely same)

**Source:** https://developers.binance.com/docs/binance-spot-api-docs/web-socket-streams

Connect to a generic endpoint, then send subscription messages:

```
wss://stream.binance.com:9443/stream
```

**Subscribe:**
```json
{
  "method": "SUBSCRIBE",
  "params": ["btcusdt@trade", "ethusdt@trade", "bnbusdt@trade"],
  "id": "any-unique-id"
}
```

**Unsubscribe:**
```json
{
  "method": "UNSUBSCRIBE",
  "params": ["bnbusdt@trade"],
  "id": "any-unique-id"
}
```

This is the mechanism for **adding/removing symbols without reconnecting**. Binance Futures almost certainly supports the same protocol (the Futures subscription docs page was unreachable at time of research; verify before implementing).

---

### 4. Constraints

| Constraint | Futures | Spot |
|---|---|---|
| Max streams per connection | **1024** | Not specified in fetched doc |
| WS message rate limit | 10 messages/second (inbound) | Not specified |
| Session duration | 24 hours (reconnect required) | Not specified |
| Ping interval | Server pings every 3 min; 10-min pong timeout = disconnect | Not specified |

**Rate limit note:** the 10 msg/sec limit applies to *outbound subscribe/unsubscribe messages*, not to *incoming trade events*. Subscribing to 1024 symbols is fine; sending 1024 SUBSCRIBE messages in one second is not.

---

### 5. Spot vs. Futures Differences

| | Spot (`stream.binance.com:9443`) | Futures (`fstream.binance.com`) |
|---|---|---|
| Multi-symbol URL | `?streams=s1/s2` | `/ws/s1/s2` or `?streams=s1/s2` |
| Combined stream wrapper | Yes (`{"stream":...,"data":...}`) | Yes |
| Dynamic subscribe | Yes | Likely yes (unconfirmed — verify) |
| Max streams | Not stated | 1024 |

The `binancefuture.com` testnet domain used in `application-local.yaml` is the **USD-M Futures testnet** — same protocol as `fstream.binance.com` production.

---

## Implications for Quantica

### Current design (one symbol, one hardcoded URL)

`WebsocketConfig.java` injects `${binance.stream}` as a single URL string into `WebSocketConnectionManager`. The entire URL (`wss://fstream.binance.com/ws/btcusdt@trade`) is owned by config. This means:

- One symbol per instance
- Changing the symbol requires a config change + restart
- No path to runtime multi-symbol without restructuring `WebsocketConfig`

### Option A — Multi-symbol via URL (simplest, no code change to handler)

Change `application-local.yaml` from:
```yaml
binance:
  stream: wss://stream.binancefuture.com/ws/btcusdt@trade
```

To:
```yaml
binance:
  stream: wss://stream.binancefuture.com/ws/btcusdt@trade/ethusdt@trade/bnbusdt@trade
```

Or make it a `${SYMBOLS}` env var that expands into a URL. This requires no handler changes because `BinanceStreamResponse` already reads the symbol from the `"s"` field of the payload. The `@KafkaListener` / `KafkaPublisher` key-by-symbol fix still applies.

**Caveat:** if using stream mode (query string), the response is wrapped in `{"stream":"...","data":{...}}` — `BinanceStreamResponse` parsing would break. Stick to WS mode (path-based) to avoid the wrapper.

### Option B — Dynamic subscribe/unsubscribe (most flexible)

Keep the connection open to `wss://fstream.binance.com/public/ws` and send SUBSCRIBE messages. `BinanceWssHandler.afterConnectionEstablished` would send the initial subscribe list; a new API endpoint or config reload could add/remove symbols at runtime.

This requires `BinanceWssHandler` to send text messages after connect — it currently only receives. More work, but enables true runtime symbol management.

### Recommendation for branch 63

**Use Option A** to close the branch goals cleanly:

1. Replace hardcoded `btcusdt` URL with `${BINANCE_SYMBOLS:btcusdt@trade}` in config, constructing the WS-mode URL as `baseUrl/ws/${BINANCE_SYMBOLS}`.
2. Support comma-separated symbol list that gets joined with `/` for the URL path.
3. Fix Kafka keying to use `order.symbol()` so multi-symbol records route to consistent partitions.

Option B is a future feature, not needed for this branch.
