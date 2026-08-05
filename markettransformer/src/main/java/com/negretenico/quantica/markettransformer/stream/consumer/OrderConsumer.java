package com.negretenico.quantica.markettransformer.stream.consumer;

import com.negretenico.quantica.markettransformer.model.BinanceStreamResponse;
import com.negretenico.quantica.markettransformer.model.events.OrderReceived;
import com.negretenico.quantica.markettransformer.validation.OrderValidationResult;
import com.negretenico.quantica.markettransformer.validation.ValidationChain;
import io.micrometer.core.annotation.Timed;
import io.micrometer.core.instrument.Counter;
import io.micrometer.core.instrument.MeterRegistry;
import lombok.extern.slf4j.Slf4j;
import org.apache.kafka.clients.consumer.ConsumerRecord;
import org.springframework.context.ApplicationEventPublisher;
import org.springframework.kafka.annotation.KafkaListener;
import org.springframework.stereotype.Component;

import java.util.concurrent.ConcurrentHashMap;

@Slf4j
@Component
public class OrderConsumer {
	private final ApplicationEventPublisher applicationEventPublisher;
	private final MeterRegistry meterRegistry;
	private final ValidationChain validationChain;
	private final ConcurrentHashMap<String, Counter> consumedCounters = new ConcurrentHashMap<>();
	private final ConcurrentHashMap<String, Counter> rejectedCounters = new ConcurrentHashMap<>();

	public OrderConsumer(ApplicationEventPublisher applicationEventPublisher, MeterRegistry meterRegistry, ValidationChain validationChain) {
		this.applicationEventPublisher = applicationEventPublisher;
		this.meterRegistry = meterRegistry;
		this.validationChain = validationChain;
	}

	@Timed(value = "quantica.stage.kafka.consume", extraTags = {"topic", "order"})
	@KafkaListener(
			topics = "order",
			groupId = "market-transformer-group",
			containerFactory = "kafkaListenerContainerFactory"
	)
	public void consumeOrder(ConsumerRecord<String, BinanceStreamResponse> record) {
		BinanceStreamResponse order = record.value();
		log.debug("Consuming order: {}",order);

		OrderValidationResult validationResult = validationChain.execute(order);
		if (!validationResult.accepted()) {
			rejectedCounters.computeIfAbsent(order.symbol(), sym ->
					Counter.builder("quantica.messages.rejected")
							.tag("symbol", sym)
							.register(meterRegistry))
					.increment();
			return;
		}

		log.debug("Producing message: OrderReceived {}",order.getId());
		applicationEventPublisher.publishEvent(OrderReceived.of(this,order));
		consumedCounters.computeIfAbsent(order.symbol(), sym ->
				Counter.builder("quantica.messages.consumed")
						.tag("topic", "order")
						.tag("symbol", sym)
						.register(meterRegistry))
				.increment();
	}
}