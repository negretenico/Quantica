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
class PriceSpikeTest {

	@Mock
	SignalPublisher kafkaPublisher;

	@Mock
	OrderReceived orderReceived1;

	@Mock
	OrderReceived orderReceived2;

	@Mock
	BinanceStreamResponse trade1;

	@Mock
	BinanceStreamResponse trade2;

	PriceSpike priceSpike;

	@BeforeEach
	void setup() {
		priceSpike = new PriceSpike(kafkaPublisher);

		// connect trades to OrderReceived events
		Mockito.when(orderReceived1.getBinanceOrder()).thenReturn(trade1);
		Mockito.when(orderReceived2.getBinanceOrder()).thenReturn(trade2);
		Mockito.when(trade1.symbol()).thenReturn("BTCUSDT");
		Mockito.when(trade2.symbol()).thenReturn("BTCUSDT");
	}

	@Test
	void givenPriceSpikeHasNotHappened_thenNoEventIsPublished() {
		Mockito.when(trade1.getPriceAsBigDecimal()).thenReturn(new BigDecimal("100"));
		Mockito.when(trade2.getPriceAsBigDecimal()).thenReturn(new BigDecimal("101")); // 1% move

		priceSpike.onApplicationEvent(orderReceived1);
		priceSpike.onApplicationEvent(orderReceived2);

		Mockito.verify(kafkaPublisher, Mockito.never()).publish(Mockito.any());
	}

	@Test
	void givenPriceSpikeHasHappened_thenEventIsPublished() {
		Mockito.when(trade1.getPriceAsBigDecimal()).thenReturn(new BigDecimal("100"));
		Mockito.when(trade2.getPriceAsBigDecimal()).thenReturn(new BigDecimal("120")); // 20% move
		Mockito.when(trade2.getTradeSide()).thenReturn(TradeIndicator.BUY);
		Mockito.when(trade2.quantity()).thenReturn("0.00");
		Mockito.when(trade2.price()).thenReturn("0.00");
		priceSpike.onApplicationEvent(orderReceived1);
		priceSpike.onApplicationEvent(orderReceived2);

		Mockito.verify(kafkaPublisher, Mockito.atLeastOnce()).publish(Mockito.any());
	}
}
