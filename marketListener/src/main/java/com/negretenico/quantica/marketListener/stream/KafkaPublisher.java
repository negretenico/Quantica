package com.negretenico.quantica.marketListener.stream;

import com.negretenico.quantica.marketListener.model.BinanceStreamResponse;
import com.negretenico.quantica.marketListener.model.events.BinanceOrderReceived;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.event.EventListener;
import org.springframework.kafka.core.KafkaTemplate;
import org.springframework.stereotype.Component;

@Slf4j
@Component
public class KafkaPublisher {
	private final KafkaTemplate<String, BinanceStreamResponse> template;
	private final String topicName;

	public KafkaPublisher(KafkaTemplate<String, BinanceStreamResponse> template
			, @Value("${market.order.topic}") String topicName) {
		this.template = template;
		this.topicName = topicName;
	}

	@EventListener(BinanceOrderReceived.class)
	public void publishToKafka(BinanceOrderReceived binanceOrderReceived) {
		BinanceStreamResponse order = binanceOrderReceived.getBinanceOrder();
		log.info("Publishing message to kafka, {}", order.getId());
		template.send(topicName, order)
				.thenAccept(result -> {
					log.info("Success on thread: {}", Thread.currentThread().getName());
					log.info("Success produced: {}", result.getProducerRecord().value());
				})
				.exceptionally(throwable -> {
					log.error("Error on thread: {}", Thread.currentThread().getName());
					log.error("Error: {} ", throwable.getLocalizedMessage());
					return null;
				});
		;
	}
}
