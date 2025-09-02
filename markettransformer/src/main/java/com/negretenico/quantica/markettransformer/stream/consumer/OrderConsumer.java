package com.negretenico.quantica.markettransformer.stream.consumer;

import com.negretenico.quantica.markettransformer.model.BinanceStreamResponse;
import com.negretenico.quantica.markettransformer.model.TradeIndicator;
import com.negretenico.quantica.markettransformer.model.events.OrderReceived;
import lombok.extern.slf4j.Slf4j;
import org.apache.kafka.clients.consumer.ConsumerRecord;
import org.springframework.context.ApplicationEventPublisher;
import org.springframework.core.annotation.Order;
import org.springframework.kafka.annotation.KafkaListener;
import org.springframework.stereotype.Component;

@Slf4j
@Component
public class OrderConsumer {
	private final ApplicationEventPublisher applicationEventPublisher;

	public OrderConsumer(ApplicationEventPublisher applicationEventPublisher) {
		this.applicationEventPublisher = applicationEventPublisher;
	}

	@KafkaListener(
			topics = "order",
			groupId = "market-transformer-group",
			containerFactory = "kafkaListenerContainerFactory"
	)
	public void consumeOrder(ConsumerRecord<String, BinanceStreamResponse> record) {
		BinanceStreamResponse order = record.value();
		log.info("Consuming order: {}",order);
		applicationEventPublisher.publishEvent(OrderReceived.of(this,order));
	}
}