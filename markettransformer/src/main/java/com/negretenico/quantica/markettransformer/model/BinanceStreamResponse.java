package com.negretenico.quantica.markettransformer.model;

import com.fasterxml.jackson.annotation.JsonIgnore;
import com.fasterxml.jackson.annotation.JsonProperty;

import java.math.BigInteger;

/**
 * Binance Trade Stream Response
 * {
 * "e": "trade",           // Event type
 * "E": 1756645835827,     // Event time (timestamp)
 * "T": 1756645835827,     // Trade time (timestamp)
 * "s": "BTCUSDT",         // Symbol
 * "t": 387235071,         // Trade ID
 * "p": "108255.20",       // Price
 * "q": "0.010",           // Quantity
 * "X": "MARKET",          // Order type
 * "m": true               // Is buyer market maker (true=sell, false=buy)
 * }
 */
public record BinanceStreamResponse(
		@JsonProperty("e") String eventType,
		@JsonProperty("E") long eventTime,
		@JsonProperty("T") long tradeTime,
		@JsonProperty("s") String symbol,
		@JsonProperty("t") long tradeId,
		@JsonProperty("p") String price,
		@JsonProperty("q") String quantity,
		@JsonProperty("X") String orderType,
		@JsonProperty("m") boolean isBuyerMarketMaker
) {

	@JsonIgnore
	public BigInteger getPriceAsBiInteger() {
		return new BigInteger(price);
	}

	@JsonIgnore
	public BigInteger getQuantityAsBigInteger() {
		return new BigInteger(quantity);
	}

	@JsonIgnore
	public TradeIndicator getTradeSide() {
		return isBuyerMarketMaker ? TradeIndicator.SELL : TradeIndicator.BUY;
	}

	public String getId() {
		return String.join("-", symbol, String.valueOf(tradeId), price, quantity,
				getTradeSide().toString());
	}
}


