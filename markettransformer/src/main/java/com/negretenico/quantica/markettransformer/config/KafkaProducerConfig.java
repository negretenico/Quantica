package com.negretenico.quantica.markettransformer.config;

import com.negretenico.quantica.markettransformer.model.BinanceStreamResponse;
import com.negretenico.quantica.markettransformer.model.events.SignalEvent;
import org.apache.kafka.clients.producer.ProducerConfig;
import org.apache.kafka.common.serialization.StringSerializer;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.kafka.core.DefaultKafkaProducerFactory;
import org.springframework.kafka.core.KafkaTemplate;
import org.springframework.kafka.core.ProducerFactory;
import org.springframework.kafka.support.serializer.JsonSerializer;

import java.util.Map;

@Configuration
public class KafkaProducerConfig {
	private final String bootstrapAddress;

	public KafkaProducerConfig(@Value("${kafka.bootstrap}") String bootstrapAddress) {
		this.bootstrapAddress = bootstrapAddress;
	}

	@Bean
	public ProducerFactory<String, SignalEvent> producerFactory() {
		Map<String, Object> configProps = Map.of(
				ProducerConfig.BOOTSTRAP_SERVERS_CONFIG, bootstrapAddress,
				ProducerConfig.KEY_SERIALIZER_CLASS_CONFIG, StringSerializer.class,
				ProducerConfig.VALUE_SERIALIZER_CLASS_CONFIG, JsonSerializer.class,
				ProducerConfig.ACKS_CONFIG, "all",
				ProducerConfig.RETRIES_CONFIG, 0,
				ProducerConfig.BATCH_SIZE_CONFIG, 16384,
				ProducerConfig.LINGER_MS_CONFIG, 1,
				JsonSerializer.ADD_TYPE_INFO_HEADERS, false,
				ProducerConfig.BUFFER_MEMORY_CONFIG, 33554432
		);
		return new DefaultKafkaProducerFactory<>(configProps);
	}

	@Bean
	public KafkaTemplate<String, SignalEvent> kafkaTemplate() {
		return new KafkaTemplate<>(producerFactory());
	}
}