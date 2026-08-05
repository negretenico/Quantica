package com.negretenico.quantica.markettransformer.stream.consumer;

import com.negretenico.quantica.markettransformer.model.BinanceStreamResponse;
import com.negretenico.quantica.markettransformer.validation.OrderValidationResult;
import com.negretenico.quantica.markettransformer.validation.ValidationChain;
import io.micrometer.core.instrument.simple.SimpleMeterRegistry;
import org.apache.kafka.clients.consumer.ConsumerRecord;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.Mockito;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.context.ApplicationEventPublisher;

import static org.junit.jupiter.api.Assertions.*;

@ExtendWith(MockitoExtension.class)
class OrderConsumerTest {
	@Mock
	ApplicationEventPublisher applicationEventPublisher;
	@Mock
	ConsumerRecord<String, BinanceStreamResponse> record;
	@Mock
	BinanceStreamResponse response;
	@Mock
	ValidationChain validationChain;
	SimpleMeterRegistry registry = new SimpleMeterRegistry();
	OrderConsumer orderConsumer;

	@BeforeEach
	void setup() {
		orderConsumer = new OrderConsumer(applicationEventPublisher, registry, validationChain);
	}

	@Test
	void consumerMessage() {
		Mockito.when(record.value()).thenReturn(response);
		Mockito.when(response.symbol()).thenReturn("BTCUSDT");
		Mockito.when(validationChain.execute(response)).thenReturn(OrderValidationResult.accept());
		Mockito.doNothing().when(applicationEventPublisher).publishEvent(Mockito.any());
		orderConsumer.consumeOrder(record);
		Mockito.verify(applicationEventPublisher, Mockito.atLeastOnce()).publishEvent(Mockito.any());
		assertEquals(1.0, registry.counter("quantica.messages.consumed", "topic", "order", "symbol", "BTCUSDT").count());
	}

	@Test
	void rejectedOrderDoesNotPublishEvent() {
		Mockito.when(record.value()).thenReturn(response);
		Mockito.when(response.symbol()).thenReturn("BTCUSDT");
		Mockito.when(validationChain.execute(response)).thenReturn(OrderValidationResult.reject("bad price"));
		orderConsumer.consumeOrder(record);
		Mockito.verify(applicationEventPublisher, Mockito.never()).publishEvent(Mockito.any());
		assertEquals(1.0, registry.counter("quantica.messages.rejected", "symbol", "BTCUSDT").count());
		assertEquals(0.0, registry.counter("quantica.messages.consumed", "topic", "order", "symbol", "BTCUSDT").count());
	}
}
