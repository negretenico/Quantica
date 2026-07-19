package com.negretenico.quantica.marketListener.stream;

import com.negretenico.quantica.marketListener.model.BinanceStreamResponse;
import com.negretenico.quantica.marketListener.model.events.BinanceOrderReceived;
import io.micrometer.core.instrument.Counter;
import io.micrometer.core.instrument.MeterRegistry;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.event.EventListener;
import org.springframework.kafka.core.KafkaTemplate;
import org.springframework.stereotype.Component;

import java.util.concurrent.ConcurrentHashMap;

@Slf4j
@Component
public class KafkaPublisher {
	private final KafkaTemplate<String, BinanceStreamResponse> template;
	private final String topicName;
	private final MeterRegistry meterRegistry;
	private final ConcurrentHashMap<String, Counter> producedCounters = new ConcurrentHashMap<>();

	public KafkaPublisher(KafkaTemplate<String, BinanceStreamResponse> template,
			@Value("${market.order.topic}") String topicName,
			MeterRegistry meterRegistry) {
		this.template = template;
		this.topicName = topicName;
		this.meterRegistry = meterRegistry;
	}

	@EventListener(BinanceOrderReceived.class)
	public void publishToKafka(BinanceOrderReceived binanceOrderReceived) {
		BinanceStreamResponse order = binanceOrderReceived.getBinanceOrder();
		log.debug("Publishing to kafka: {}", order.getId());
		template.send(topicName, order)
				.thenAccept(result -> {
					log.debug("Produced: {}", result.getProducerRecord().value().getId());
					producedCounters.computeIfAbsent(order.symbol(), sym ->
							Counter.builder("quantica.messages.produced")
									.tag("topic", topicName)
									.tag("symbol", sym)
									.register(meterRegistry))
							.increment();
				})
				.exceptionally(throwable -> {
					log.error("Error on thread: {}", Thread.currentThread().getName());
					log.error("Error: {} ", throwable.getLocalizedMessage());
					return null;
				});
		;
	}
}
