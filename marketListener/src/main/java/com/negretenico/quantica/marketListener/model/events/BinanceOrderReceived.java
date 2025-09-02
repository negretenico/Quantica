package com.negretenico.quantica.marketListener.model.events;

import com.negretenico.quantica.marketListener.model.BinanceStreamResponse;
import org.springframework.context.ApplicationEvent;

public class BinanceOrderReceived extends ApplicationEvent {
	BinanceStreamResponse binanceStreamResponse;

	private BinanceOrderReceived(Object source, BinanceStreamResponse binanceStreamResponse) {
		super(source);
		this.binanceStreamResponse = binanceStreamResponse;
	}

	public static BinanceOrderReceived of(Object source,
																				BinanceStreamResponse binanceStreamResponse) {
		return new BinanceOrderReceived(source, binanceStreamResponse);
	}

	public BinanceStreamResponse getBinanceOrder() {
		return binanceStreamResponse;
	}
}
