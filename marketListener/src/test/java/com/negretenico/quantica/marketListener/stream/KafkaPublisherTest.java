package com.negretenico.quantica.marketListener.stream;

import com.negretenico.quantica.marketListener.model.BinanceStreamResponse;
import com.negretenico.quantica.marketListener.model.events.BinanceOrderReceived;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.kafka.core.KafkaTemplate;
import org.springframework.kafka.support.SendResult;

import java.util.concurrent.CompletableFuture;

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

	KafkaPublisher publisher;

	@BeforeEach
	void setup() {
		publisher = new KafkaPublisher(template, "topicName");
	}

	@Test
	void success() {
		// Setup the mock chain
		when(binanceOrderReceived.getBinanceOrder()).thenReturn(binanceStreamResponse);
		when(binanceStreamResponse.getId()).thenReturn("test-id");

		// Mock the KafkaTemplate.send() to return a successful CompletableFuture
		when(template.send(anyString(), any(BinanceStreamResponse.class)))
				.thenReturn(CompletableFuture.completedFuture(sendResult));

		// Execute the method under test
		publisher.publishToKafka(binanceOrderReceived);

		// Verify interactions
		verify(binanceOrderReceived).getBinanceOrder();
		verify(template).send("topicName", binanceStreamResponse);
	}

	@Test
	void failure() {
		// Setup the mock chain
		when(binanceOrderReceived.getBinanceOrder()).thenReturn(binanceStreamResponse);
		when(binanceStreamResponse.getId()).thenReturn("test-id");

		// Mock the KafkaTemplate.send() to return a failed CompletableFuture
		CompletableFuture<SendResult<String, BinanceStreamResponse>> failedFuture =
				CompletableFuture.failedFuture(new RuntimeException("Kafka send failed"));
		when(template.send(anyString(), any(BinanceStreamResponse.class)))
				.thenReturn(failedFuture);

		// Execute the method under test
		publisher.publishToKafka(binanceOrderReceived);

		// Verify interactions
		verify(binanceOrderReceived).getBinanceOrder();
		verify(template).send("topicName", binanceStreamResponse);
	}

	@Test
	void successWithRealBinanceStreamResponse() {
		// Create a real BinanceStreamResponse for more realistic testing
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
		when(template.send(anyString(), any(BinanceStreamResponse.class)))
				.thenReturn(CompletableFuture.completedFuture(sendResult));

		publisher.publishToKafka(binanceOrderReceived);

		verify(binanceOrderReceived).getBinanceOrder();
		verify(template).send("topicName", realResponse);
	}
}