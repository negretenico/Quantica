package com.negretenico.quantica.markettransformer.event;

import com.negretenico.quantica.markettransformer.model.BinanceStreamResponse;
import com.negretenico.quantica.markettransformer.model.TradeIndicator;
import com.negretenico.quantica.markettransformer.model.events.OrderReceived;
import com.negretenico.quantica.markettransformer.stream.producer.KafkaPublisher;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.Mockito;
import org.mockito.junit.jupiter.MockitoExtension;

import java.util.stream.IntStream;

@ExtendWith(MockitoExtension.class)
class AggressiveBuyerSellerTest {

	@Mock
	KafkaPublisher kafkaPublisher;

	@Mock
	OrderReceived orderReceived;

	@Mock
	BinanceStreamResponse buyTrade;

	@Mock
	BinanceStreamResponse sellTrade;

	AggressiveBuyerSeller transformer;

	@BeforeEach
	void setup() {
		transformer = new AggressiveBuyerSeller(kafkaPublisher);
		Mockito.when(orderReceived.getBinanceOrder()).thenReturn(buyTrade);
	}

	@Test
	void givenBuyHasNotMetThreshold_thenNoEventIsPublished() {
		Mockito.when(buyTrade.getTradeSide()).thenReturn(TradeIndicator.BUY);

		// simulate 3 trades (< threshold 5)
		IntStream.range(0, 3).forEach(i -> transformer.onApplicationEvent(orderReceived));

		Mockito.verify(kafkaPublisher, Mockito.never()).publish(Mockito.any());
	}

	@Test
	void givenBuyHasMetThreshold_thenEventIsPublished() {
		Mockito.when(buyTrade.getTradeSide()).thenReturn(TradeIndicator.BUY);
		Mockito.when(buyTrade.quantity()).thenReturn("0.00");
		Mockito.when(buyTrade.price()).thenReturn("0.00");
		// simulate 5 trades (threshold)
		IntStream.range(0, 5).forEach(i -> transformer.onApplicationEvent(orderReceived));

		Mockito.verify(kafkaPublisher, Mockito.atLeastOnce()).publish(Mockito.any());
	}

	@Test
	void givenSideFlipsBeforeThreshold_thenNoEventIsPublished() {
		Mockito.when(buyTrade.getTradeSide()).thenReturn(TradeIndicator.BUY);
		Mockito.when(sellTrade.getTradeSide()).thenReturn(TradeIndicator.SELL);

		IntStream.range(0, 2).forEach(i -> transformer.onApplicationEvent(orderReceived));

		Mockito.when(orderReceived.getBinanceOrder()).thenReturn(sellTrade);
		transformer.onApplicationEvent(orderReceived);

		Mockito.verify(kafkaPublisher, Mockito.never()).publish(Mockito.any());
	}
}
