package com.negretenico.quantica.markettransformer.stream.producer;

import com.negretenico.quantica.markettransformer.config.RabbitConfig;
import com.negretenico.quantica.markettransformer.model.events.SignalEvent;
import lombok.extern.slf4j.Slf4j;
import org.springframework.amqp.rabbit.core.RabbitTemplate;
import org.springframework.stereotype.Service;

@Service
@Slf4j
public class SignalPublisher {

	private final RabbitTemplate rabbitTemplate;

	public SignalPublisher(RabbitTemplate rabbitTemplate) {
		this.rabbitTemplate = rabbitTemplate;
	}

	public void publish(SignalEvent signal) {
		rabbitTemplate.convertAndSend(RabbitConfig.EXCHANGE, "", signal);
		log.info("Published signal: {}", signal);
	}
}
