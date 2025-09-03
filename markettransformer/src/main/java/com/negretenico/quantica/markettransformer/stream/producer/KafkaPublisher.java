package com.negretenico.quantica.markettransformer.stream.producer;

import com.negretenico.quantica.markettransformer.model.BinanceStreamResponse;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.kafka.core.KafkaTemplate;
import org.springframework.stereotype.Service;

@Service
@Slf4j
public class KafkaPublisher {
	private final KafkaTemplate<String, BinanceStreamResponse> template;
	private final String topicName;
	public KafkaPublisher(KafkaTemplate<String, BinanceStreamResponse> template
			,@Value("${market.order.name}") String topicName) {
		this.template = template;
		this.topicName = topicName;
	}
	public void publish(BinanceStreamResponse order){
		template.send(topicName,order)
				.thenAccept(result -> {
					log.info("Success produced: {}", result.getProducerRecord().value());
				})
				.exceptionally(throwable -> {
					log.error("Error: {} ", throwable.getLocalizedMessage());
					return null;
				});
	}
}
