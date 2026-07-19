package com.negretenico.quantica.markettransformer.stream.consumer;

import com.negretenico.quantica.markettransformer.model.BinanceStreamResponse;
import com.negretenico.quantica.markettransformer.model.TradeIndicator;
import com.negretenico.quantica.markettransformer.model.events.OrderReceived;
import io.micrometer.core.instrument.Counter;
import io.micrometer.core.instrument.MeterRegistry;
import lombok.extern.slf4j.Slf4j;
import org.apache.kafka.clients.consumer.ConsumerRecord;
import org.springframework.context.ApplicationEventPublisher;
import org.springframework.core.annotation.Order;
import org.springframework.kafka.annotation.KafkaListener;
import org.springframework.stereotype.Component;

import java.util.concurrent.ConcurrentHashMap;

@Slf4j
@Component
public class OrderConsumer {
	private final ApplicationEventPublisher applicationEventPublisher;
	private final MeterRegistry meterRegistry;
	private final ConcurrentHashMap<String, Counter> consumedCounters = new ConcurrentHashMap<>();

	public OrderConsumer(ApplicationEventPublisher applicationEventPublisher, MeterRegistry meterRegistry) {
		this.applicationEventPublisher = applicationEventPublisher;
		this.meterRegistry = meterRegistry;
	}

	@KafkaListener(
			topics = "order",
			groupId = "market-transformer-group",
			containerFactory = "kafkaListenerContainerFactory"
	)
	public void consumeOrder(ConsumerRecord<String, BinanceStreamResponse> record) {
		BinanceStreamResponse order = record.value();
		log.debug("Consuming order: {}",order);
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