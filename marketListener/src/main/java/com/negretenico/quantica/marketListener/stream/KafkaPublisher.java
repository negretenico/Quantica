package com.negretenico.quantica.marketListener.stream;

import com.negretenico.quantica.marketListener.config.KafkaProperties;
import com.negretenico.quantica.marketListener.model.BinanceStreamResponse;
import com.negretenico.quantica.marketListener.model.events.BinanceOrderReceived;
import io.micrometer.core.instrument.Counter;
import io.micrometer.core.instrument.MeterRegistry;
import io.micrometer.core.instrument.Timer;
import lombok.extern.slf4j.Slf4j;
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
	private final Timer produceTimer;
	private final ConcurrentHashMap<String, Counter> producedCounters = new ConcurrentHashMap<>();

	public KafkaPublisher(KafkaTemplate<String, BinanceStreamResponse> template,
			KafkaProperties kafkaProperties,
			MeterRegistry meterRegistry) {
		this.template = template;
		this.topicName = kafkaProperties.orderTopic();
		this.meterRegistry = meterRegistry;
		this.produceTimer = Timer.builder("quantica.stage.kafka.produce")
				.tag("topic", topicName)
				.register(meterRegistry);
	}

	@EventListener(BinanceOrderReceived.class)
	public void publishToKafka(BinanceOrderReceived binanceOrderReceived) {
		BinanceStreamResponse order = binanceOrderReceived.getBinanceOrder();
		log.debug("Publishing to kafka: {}", order.getId());
		Timer.Sample sample = Timer.start(meterRegistry);
		template.send(topicName, order.symbol(), order)
				.thenAccept(result -> {
					log.debug("Produced: {}", result.getProducerRecord().value().getId());
					sample.stop(produceTimer);
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
	}
}
