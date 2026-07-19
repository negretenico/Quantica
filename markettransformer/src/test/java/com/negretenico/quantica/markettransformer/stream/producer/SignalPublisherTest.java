package com.negretenico.quantica.markettransformer.stream.producer;

import com.negretenico.quantica.markettransformer.model.SignalEventType;
import com.negretenico.quantica.markettransformer.model.TradeIndicator;
import com.negretenico.quantica.markettransformer.model.events.SignalEvent;
import io.micrometer.core.instrument.simple.SimpleMeterRegistry;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.Mockito;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.amqp.rabbit.core.RabbitTemplate;

import java.util.Map;

import static org.junit.jupiter.api.Assertions.assertEquals;

@ExtendWith(MockitoExtension.class)
class SignalPublisherTest {

	@Mock
	RabbitTemplate rabbitTemplate;

	SimpleMeterRegistry registry = new SimpleMeterRegistry();
	SignalPublisher signalPublisher;

	@BeforeEach
	void setup() {
		signalPublisher = new SignalPublisher(rabbitTemplate, registry);
	}

	@Test
	void publishIncrementsCounter() {
		SignalEvent signal = new SignalEvent(
				"BTCUSDT",
				System.currentTimeMillis(),
				SignalEventType.LARGE_TRADE,
				"test reason",
				50000.0,
				0.001,
				TradeIndicator.BUY,
				Map.of()
		);
		Mockito.doNothing().when(rabbitTemplate).convertAndSend(Mockito.anyString(), Mockito.anyString(), Mockito.any(SignalEvent.class));

		signalPublisher.publish(signal);

		assertEquals(1.0, registry.counter("quantica.messages.produced", "topic", "signal", "symbol", "BTCUSDT").count());
	}
}
