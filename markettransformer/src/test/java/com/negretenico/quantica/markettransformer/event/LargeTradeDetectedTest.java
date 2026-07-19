package com.negretenico.quantica.markettransformer.event;

import com.negretenico.quantica.markettransformer.model.BinanceStreamResponse;
import com.negretenico.quantica.markettransformer.model.TradeIndicator;
import com.negretenico.quantica.markettransformer.model.events.OrderReceived;
import com.negretenico.quantica.markettransformer.stream.producer.SignalPublisher;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.Mockito;
import org.mockito.junit.jupiter.MockitoExtension;

import java.math.BigDecimal;

@ExtendWith(MockitoExtension.class)
class LargeTradeDetectedTest {
	@Mock
	SignalPublisher kafkaPublisher;
	@Mock
	OrderReceived orderReceived;
	@Mock
	BinanceStreamResponse binanceStreamResponse;

	LargeTradeDetected largeTradeDetected;

	@BeforeEach
	void setup() {
		largeTradeDetected = new LargeTradeDetected(kafkaPublisher);
	}

	void mockAll(String amount) {
		Mockito.when(orderReceived.getBinanceOrder()).thenReturn(binanceStreamResponse);
		Mockito.when(binanceStreamResponse.getQuantityAsBigDecimal()).thenReturn(new BigDecimal(amount));
	}

	@Test
	void givenAQuantityOverAMillionIShouldPublishAnEvent() {
		mockAll("10000000");
		Mockito.doNothing().when(kafkaPublisher).publish(Mockito.any());
		Mockito.when(binanceStreamResponse.getTradeSide()).thenReturn(TradeIndicator.BUY);
		Mockito.when(binanceStreamResponse.quantity()).thenReturn("0.00");
		Mockito.when(binanceStreamResponse.price()).thenReturn("0.00");
		largeTradeDetected.onApplicationEvent(orderReceived);
		Mockito.verify(kafkaPublisher, Mockito.atLeastOnce()).publish(Mockito.any());
	}

	@Test
	void givenAQuantityLessThanAMillionIShouldNotPublishAnEvent() {
		mockAll("1");
		largeTradeDetected.onApplicationEvent(orderReceived);
		Mockito.verify(kafkaPublisher, Mockito.never()).publish(Mockito.any());
	}
}
