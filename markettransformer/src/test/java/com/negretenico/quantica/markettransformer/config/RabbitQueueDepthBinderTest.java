package com.negretenico.quantica.markettransformer.config;

import io.micrometer.core.instrument.simple.SimpleMeterRegistry;
import okhttp3.mockwebserver.MockResponse;
import okhttp3.mockwebserver.MockWebServer;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.web.reactive.function.client.WebClient;

import java.io.IOException;

import static org.assertj.core.api.Assertions.assertThat;

class RabbitQueueDepthBinderTest {

	private MockWebServer mockWebServer;
	private SimpleMeterRegistry registry;

	@BeforeEach
	void setup() throws IOException {
		mockWebServer = new MockWebServer();
		mockWebServer.start();
		WebClient webClient = WebClient.builder()
				.baseUrl(mockWebServer.url("/").toString())
				.build();
		registry = new SimpleMeterRegistry();
		new RabbitQueueDepthBinder(webClient).bindTo(registry);
	}

	@AfterEach
	void teardown() throws IOException {
		mockWebServer.shutdown();
	}

	@Test
	void returnsQueueDepthForAnalysisQueue() {
		mockWebServer.enqueue(new MockResponse()
				.setBody("{\"messages\": 42}")
				.addHeader("Content-Type", "application/json"));

		double depth = registry.get("rabbitmq.queue.messages")
				.tag("queue", RabbitConfig.ANALYSIS_QUEUE)
				.gauge().value();

		assertThat(depth).isEqualTo(42.0);
	}

	@Test
	void returnsZeroOnServerError() {
		mockWebServer.enqueue(new MockResponse().setResponseCode(500));

		double depth = registry.get("rabbitmq.queue.messages")
				.tag("queue", RabbitConfig.ANALYSIS_QUEUE)
				.gauge().value();

		assertThat(depth).isEqualTo(0.0);
	}

	@Test
	void returnsZeroOnConnectionFailure() throws IOException {
		mockWebServer.shutdown();

		double depth = registry.get("rabbitmq.queue.messages")
				.tag("queue", RabbitConfig.ANALYSIS_QUEUE)
				.gauge().value();

		assertThat(depth).isEqualTo(0.0);
	}
}
