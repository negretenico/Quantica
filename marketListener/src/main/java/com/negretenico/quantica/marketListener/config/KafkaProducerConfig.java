package com.negretenico.quantica.marketListener.config;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.negretenico.quantica.marketListener.model.BinanceStreamResponse;
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
	private final ObjectMapper objectMapper;

	public KafkaProducerConfig(@Value("${kafka.bootstrap}") String bootstrapAddress, ObjectMapper objectMapper) {
		this.bootstrapAddress = bootstrapAddress;
		this.objectMapper = objectMapper;
	}

	@Bean
	public ProducerFactory<String, BinanceStreamResponse> producerFactory() {
		JsonSerializer<BinanceStreamResponse> valueSerializer = new JsonSerializer<>(objectMapper);
		valueSerializer.setAddTypeInfo(false);
		return new DefaultKafkaProducerFactory<>(
				Map.of(
						ProducerConfig.BOOTSTRAP_SERVERS_CONFIG, bootstrapAddress,
						ProducerConfig.ACKS_CONFIG, "all",
						ProducerConfig.RETRIES_CONFIG, 0,
						ProducerConfig.BATCH_SIZE_CONFIG, 16384,
						ProducerConfig.LINGER_MS_CONFIG, 1,
						ProducerConfig.BUFFER_MEMORY_CONFIG, 33554432
				),
				new StringSerializer(),
				valueSerializer
		);
	}

	@Bean
	public KafkaTemplate<String, BinanceStreamResponse> kafkaTemplate() {
		return new KafkaTemplate<>(producerFactory());
	}
}
