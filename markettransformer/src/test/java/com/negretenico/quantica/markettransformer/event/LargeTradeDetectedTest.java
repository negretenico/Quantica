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
class LargeTradeDetectedTest {
	@Mock
	KafkaPublisher kafkaPublisher;
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
		Mockito.when(binanceStreamResponse.getQuantityAsBigDecimal()).thenReturn(new BigInteger(amount));
	}

	@Test
	void givenAQuantityOverAMillionIShouldPublishAnEvent() {
		mockAll("10000000");
		Mockito.doNothing().when(kafkaPublisher).publish(Mockito.any());
		largeTradeDetected.onApplicationEvent(orderReceived);
		Mockito.verify(kafkaPublisher,Mockito.atLeastOnce()).publish(Mockito.any());
	}
	@Test
	void givenAQuantityLessThanAMillionIShouldNotPublishAnEvent(){
		mockAll("1");
		largeTradeDetected.onApplicationEvent(orderReceived);
		Mockito.verify(kafkaPublisher,Mockito.never()).publish(Mockito.any());
	}
}