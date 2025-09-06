package model

// BinanceStreamResponse represents a trade stream response from Binance.
// Example:
// {
//   "e": "trade",
//   "E": 1756645835827,
//   "T": 1756645835827,
//   "s": "BTCUSDT",
//   "t": 387235071,
//   "p": "108255.20",
//   "q": "0.010",
//   "X": "MARKET",
//   "m": true
// }
type BinanceStreamResponse struct {
    EventType          string `json:"e"` // Event type
    EventTime          int64  `json:"E"` // Event time (timestamp)
    TradeTime          int64  `json:"T"` // Trade time (timestamp)
    Symbol             string `json:"s"` // Symbol
    TradeID            int64  `json:"t"` // Trade ID
    Price              string `json:"p"` // Price (as string, use decimal for math)
    Quantity           string `json:"q"` // Quantity (as string, use decimal for math)
    OrderType          string `json:"X"` // Order type
    IsBuyerMarketMaker bool   `json:"m"` // True = sell, False = buy
}
