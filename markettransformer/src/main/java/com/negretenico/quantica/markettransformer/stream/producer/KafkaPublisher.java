package com.negretenico.quantica.markettransformer.stream.producer;

import com.negretenico.quantica.markettransformer.model.BinanceStreamResponse;
import com.negretenico.quantica.markettransformer.model.events.SignalEvent;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.kafka.core.KafkaTemplate;
import org.springframework.stereotype.Service;

@Service
@Slf4j
public class KafkaPublisher {
	private final KafkaTemplate<String, SignalEvent> template;
	private final String topicName;
	public KafkaPublisher(KafkaTemplate<String, SignalEvent> template
			,@Value("${market.signal.topic}") String topicName) {
		this.template = template;
		this.topicName = topicName;
	}
	public void publish(SignalEvent order){
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
