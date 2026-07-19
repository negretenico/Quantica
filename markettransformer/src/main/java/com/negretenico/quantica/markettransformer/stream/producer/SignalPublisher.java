package com.negretenico.quantica.markettransformer.stream.producer;

import com.negretenico.quantica.markettransformer.config.RabbitConfig;
import com.negretenico.quantica.markettransformer.model.events.SignalEvent;
import io.micrometer.core.instrument.Counter;
import io.micrometer.core.instrument.MeterRegistry;
import lombok.extern.slf4j.Slf4j;
import org.springframework.amqp.rabbit.core.RabbitTemplate;
import org.springframework.stereotype.Service;

import java.util.concurrent.ConcurrentHashMap;

@Service
@Slf4j
public class SignalPublisher {

	private final RabbitTemplate rabbitTemplate;
	private final MeterRegistry meterRegistry;
	private final ConcurrentHashMap<String, Counter> producedCounters = new ConcurrentHashMap<>();

	public SignalPublisher(RabbitTemplate rabbitTemplate, MeterRegistry meterRegistry) {
		this.rabbitTemplate = rabbitTemplate;
		this.meterRegistry = meterRegistry;
	}

	public void publish(SignalEvent signal) {
		rabbitTemplate.convertAndSend(RabbitConfig.EXCHANGE, "", signal);
		log.info("Published signal: {}", signal);
		producedCounters.computeIfAbsent(signal.symbol(), sym ->
				Counter.builder("quantica.messages.produced")
						.tag("topic", "signal")
						.tag("symbol", sym)
						.register(meterRegistry))
				.increment();
	}
}
