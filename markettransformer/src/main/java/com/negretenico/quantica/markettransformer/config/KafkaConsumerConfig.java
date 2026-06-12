package com.negretenico.quantica.markettransformer.config;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.negretenico.quantica.markettransformer.model.BinanceStreamResponse;
import com.negretenico.quantica.markettransformer.model.KafkaProperties;
import org.apache.kafka.clients.consumer.ConsumerConfig;
import org.apache.kafka.common.serialization.StringDeserializer;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.kafka.config.ConcurrentKafkaListenerContainerFactory;
import org.springframework.kafka.core.ConsumerFactory;
import org.springframework.kafka.core.DefaultKafkaConsumerFactory;
import org.springframework.kafka.support.serializer.JsonDeserializer;

import java.util.Map;

@Configuration
public class KafkaConsumerConfig {
	private final KafkaProperties kafkaProperties;
	private final ObjectMapper objectMapper;

	public KafkaConsumerConfig(KafkaProperties kafkaProperties, ObjectMapper objectMapper) {
		this.kafkaProperties = kafkaProperties;
		this.objectMapper = objectMapper;
	}

	@Bean
	public ConsumerFactory<String, BinanceStreamResponse> consumerFactory() {
		JsonDeserializer<BinanceStreamResponse> deserializer = new JsonDeserializer<>(BinanceStreamResponse.class, objectMapper);
		deserializer.setRemoveTypeHeaders(true);
		deserializer.addTrustedPackages("*");
		return new DefaultKafkaConsumerFactory<>(
				Map.of(
						ConsumerConfig.BOOTSTRAP_SERVERS_CONFIG, kafkaProperties.bootstrap(),
						ConsumerConfig.GROUP_ID_CONFIG, kafkaProperties.groupId()
				),
				new StringDeserializer(),
				deserializer
		);
	}

	@Bean
	public ConcurrentKafkaListenerContainerFactory<String, BinanceStreamResponse> kafkaListenerContainerFactory() {
		ConcurrentKafkaListenerContainerFactory<String, BinanceStreamResponse> factory = new ConcurrentKafkaListenerContainerFactory<>();
		factory.setConsumerFactory(consumerFactory());
		return factory;
	}
}
