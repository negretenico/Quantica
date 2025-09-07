package com.negretenico.quantica.markettransformer.model.events;

import com.negretenico.quantica.markettransformer.model.SignalEventType;
import com.negretenico.quantica.markettransformer.model.TradeIndicator;

import java.util.Map;

public record SignalEvent(
		String symbol,
		long eventTime,
		SignalEventType type,
		String reason,
		double price,
		double quantity,
		TradeIndicator side,
		Map<String, Object> metadata
) {}
