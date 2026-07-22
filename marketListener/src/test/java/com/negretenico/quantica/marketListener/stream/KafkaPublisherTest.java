package com.negretenico.quantica.marketListener.stream;

import com.negretenico.quantica.marketListener.config.KafkaProperties;
import com.negretenico.quantica.marketListener.model.BinanceStreamResponse;
import com.negretenico.quantica.marketListener.model.events.BinanceOrderReceived;
import io.micrometer.core.instrument.simple.SimpleMeterRegistry;
import org.apache.kafka.clients.producer.ProducerRecord;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.kafka.core.KafkaTemplate;
import org.springframework.kafka.support.SendResult;

import java.util.concurrent.CompletableFuture;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

@ExtendWith(MockitoExtension.class)
class KafkaPublisherTest {
	@Mock
	KafkaTemplate<String, BinanceStreamResponse> template;

	@Mock
	BinanceOrderReceived binanceOrderReceived;

	@Mock
	BinanceStreamResponse binanceStreamResponse;

	@Mock
	SendResult<String, BinanceStreamResponse> sendResult;

	@Mock
	ProducerRecord<String, BinanceStreamResponse> producerRecord;

	SimpleMeterRegistry registry = new SimpleMeterRegistry();
	KafkaPublisher publisher;

	@BeforeEach
	void setup() {
		publisher = new KafkaPublisher(template, new KafkaProperties("localhost:9092", "topicName", 4, (short) 1), registry);
	}

	@Test
	void success() {
		when(binanceOrderReceived.getBinanceOrder()).thenReturn(binanceStreamResponse);
		when(binanceStreamResponse.getId()).thenReturn("test-id");
		when(binanceStreamResponse.symbol()).thenReturn("BTCUSDT");
		when(sendResult.getProducerRecord()).thenReturn(producerRecord);
		when(producerRecord.value()).thenReturn(binanceStreamResponse);

		when(template.send(anyString(), anyString(), any(BinanceStreamResponse.class)))
				.thenReturn(CompletableFuture.completedFuture(sendResult));

		publisher.publishToKafka(binanceOrderReceived);

		verify(binanceOrderReceived).getBinanceOrder();
		verify(template).send("topicName", "BTCUSDT", binanceStreamResponse);
		assertEquals(1.0, registry.counter("quantica.messages.produced", "topic", "topicName", "symbol", "BTCUSDT").count());
	}

	@Test
	void failure() {
		when(binanceOrderReceived.getBinanceOrder()).thenReturn(binanceStreamResponse);
		when(binanceStreamResponse.getId()).thenReturn("test-id");
		when(binanceStreamResponse.symbol()).thenReturn("BTCUSDT");

		CompletableFuture<SendResult<String, BinanceStreamResponse>> failedFuture =
				CompletableFuture.failedFuture(new RuntimeException("Kafka send failed"));
		when(template.send(anyString(), anyString(), any(BinanceStreamResponse.class)))
				.thenReturn(failedFuture);

		publisher.publishToKafka(binanceOrderReceived);

		verify(binanceOrderReceived).getBinanceOrder();
		verify(template).send("topicName", "BTCUSDT", binanceStreamResponse);
		assertEquals(0.0, registry.counter("quantica.messages.produced", "topic", "topicName", "symbol", "BTCUSDT").count());
	}

	@Test
	void successWithRealBinanceStreamResponse() {
		BinanceStreamResponse realResponse = new BinanceStreamResponse(
				"trade",
				System.currentTimeMillis(),
				System.currentTimeMillis(),
				"BTCUSDT",
				123456L,
				"50000.00",
				"0.001",
				"MARKET",
				false
		);

		when(binanceOrderReceived.getBinanceOrder()).thenReturn(realResponse);
		when(sendResult.getProducerRecord()).thenReturn(producerRecord);
		when(producerRecord.value()).thenReturn(realResponse);
		when(template.send(anyString(), anyString(), any(BinanceStreamResponse.class)))
				.thenReturn(CompletableFuture.completedFuture(sendResult));

		publisher.publishToKafka(binanceOrderReceived);

		verify(binanceOrderReceived).getBinanceOrder();
		verify(template).send("topicName", "BTCUSDT", realResponse);
		assertEquals(1.0, registry.counter("quantica.messages.produced", "topic", "topicName", "symbol", "BTCUSDT").count());
	}
}