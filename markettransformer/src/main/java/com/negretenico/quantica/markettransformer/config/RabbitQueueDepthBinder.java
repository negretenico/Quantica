package com.negretenico.quantica.markettransformer.config;

import io.micrometer.core.instrument.Gauge;
import io.micrometer.core.instrument.MeterRegistry;
import io.micrometer.core.instrument.binder.MeterBinder;
import lombok.extern.slf4j.Slf4j;
import org.springframework.http.HttpStatusCode;
import org.springframework.stereotype.Component;
import org.springframework.web.reactive.function.client.WebClient;
import org.springframework.web.util.UriUtils;
import reactor.core.publisher.Mono;

import java.nio.charset.StandardCharsets;
import java.util.List;

/**
 * Binds RabbitMQ queue depth as Micrometer gauges. The gauge supplier is called synchronously
 * on each Prometheus scrape via the RabbitMQ management HTTP API.
 * Credentials must be embedded in {@code rabbitmq.management.url}
 * (e.g. {@code http://guest:guest@localhost:15672}).
 */
@Component
@Slf4j
public class RabbitQueueDepthBinder implements MeterBinder {

	record QueueDepthResponse(double messages) {}

	private final WebClient webClient;

	public RabbitQueueDepthBinder(WebClient rabbitManagementWebClient) {
		this.webClient = rabbitManagementWebClient;
	}

	@Override
	public void bindTo(MeterRegistry registry) {
		// Alert: depth > 1000 indicates downstream consumer falling behind
		for (String queueName : List.of(RabbitConfig.ANALYSIS_QUEUE, RabbitConfig.BARD_QUEUE)) {
			Gauge.builder("rabbitmq.queue.messages", this, binder -> binder.fetchDepth(queueName))
					.tag("queue", queueName)
					.description("Number of messages in queue")
					.register(registry);
		}
	}

	private double fetchDepth(String queueName) {
		String encodedQueue = UriUtils.encode(queueName, StandardCharsets.UTF_8);
		return webClient.get()
				.uri("/api/queues/%2F/" + encodedQueue)
				.retrieve()
				.onStatus(HttpStatusCode::isError, response ->
						Mono.error(new RuntimeException("Management API returned " + response.statusCode())))
				.bodyToMono(QueueDepthResponse.class)
				.onErrorResume(e -> {
					log.warn("Failed to fetch RabbitMQ queue depth for {}: {}", queueName, e.getMessage());
					return Mono.empty();
				})
				.blockOptional()
				.map(QueueDepthResponse::messages)
				.orElse(0.0);
	}
}
