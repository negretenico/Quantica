package com.negretenico.quantica.markettransformer.event;

import com.negretenico.quantica.markettransformer.model.BinanceStreamResponse;
import com.negretenico.quantica.markettransformer.model.events.OrderReceived;
import com.negretenico.quantica.markettransformer.stream.producer.KafkaPublisher;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.Mockito;
import org.mockito.junit.jupiter.MockitoExtension;

import java.math.BigInteger;

@ExtendWith(MockitoExtension.class)
class PriceSpikeTest {

	@Mock
	KafkaPublisher kafkaPublisher;

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
	}

	@Test
	void givenPriceSpikeHasNotHappened_thenNoEventIsPublished() {
		Mockito.when(trade1.getPriceAsBiInteger()).thenReturn(new BigInteger("100"));
		Mockito.when(trade2.getPriceAsBiInteger()).thenReturn(new BigInteger("101")); // 1% move

		priceSpike.onApplicationEvent(orderReceived1);
		priceSpike.onApplicationEvent(orderReceived2);

		Mockito.verify(kafkaPublisher, Mockito.never()).publish(Mockito.any());
	}

	@Test
	void givenPriceSpikeHasHappened_thenEventIsPublished() {
		Mockito.when(trade1.getPriceAsBiInteger()).thenReturn(new BigInteger("100"));
		Mockito.when(trade2.getPriceAsBiInteger()).thenReturn(new BigInteger("120")); // 20% move

		priceSpike.onApplicationEvent(orderReceived1);
		priceSpike.onApplicationEvent(orderReceived2);

		Mockito.verify(kafkaPublisher, Mockito.atLeastOnce()).publish(trade2);
	}
}
