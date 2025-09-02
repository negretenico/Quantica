package com.negretenico.quantica.markettransformer.model.events;

import com.negretenico.quantica.markettransformer.model.BinanceStreamResponse;
import org.springframework.context.ApplicationEvent;

public class OrderReceived extends ApplicationEvent {
	BinanceStreamResponse binanceStreamResponse;

	private OrderReceived(Object source, BinanceStreamResponse binanceStreamResponse) {
		super(source);
		this.binanceStreamResponse = binanceStreamResponse;
	}

	public static OrderReceived of(Object source,
																				BinanceStreamResponse binanceStreamResponse) {
		return new OrderReceived(source, binanceStreamResponse);
	}

	public BinanceStreamResponse getBinanceOrder() {
		return binanceStreamResponse;
	}
}