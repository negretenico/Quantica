package com.negretenico.quantica.markettransformer.config;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.negretenico.quantica.markettransformer.model.BinanceStreamResponse;
import com.negretenico.quantica.markettransformer.model.KafkaProperties;
import io.micrometer.core.aop.TimedAspect;
import io.micrometer.core.instrument.MeterRegistry;
import org.apache.kafka.clients.consumer.ConsumerConfig;
import org.apache.kafka.common.serialization.StringDeserializer;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.kafka.config.ConcurrentKafkaListenerContainerFactory;
import org.springframework.kafka.core.ConsumerFactory;
import org.springframework.kafka.core.DefaultKafkaConsumerFactory;
import org.springframework.kafka.core.MicrometerConsumerListener;
import org.springframework.kafka.support.serializer.JsonDeserializer;

import java.util.Map;

@Configuration
public class KafkaConsumerConfig {
	private final KafkaProperties kafkaProperties;
	private final ObjectMapper objectMapper;
	private final MeterRegistry meterRegistry;

	public KafkaConsumerConfig(KafkaProperties kafkaProperties, ObjectMapper objectMapper, MeterRegistry meterRegistry) {
		this.kafkaProperties = kafkaProperties;
		this.objectMapper = objectMapper;
		this.meterRegistry = meterRegistry;
	}

	@Bean
	public TimedAspect timedAspect() {
		return new TimedAspect(meterRegistry);
	}

	@Bean
	public ConsumerFactory<String, BinanceStreamResponse> consumerFactory() {
		JsonDeserializer<BinanceStreamResponse> deserializer = new JsonDeserializer<>(BinanceStreamResponse.class, objectMapper);
		deserializer.setRemoveTypeHeaders(true);
		deserializer.addTrustedPackages("*");
		DefaultKafkaConsumerFactory<String, BinanceStreamResponse> factory = new DefaultKafkaConsumerFactory<>(
				Map.of(
						ConsumerConfig.BOOTSTRAP_SERVERS_CONFIG, kafkaProperties.bootstrap(),
						ConsumerConfig.GROUP_ID_CONFIG, kafkaProperties.groupId(),
						ConsumerConfig.ALLOW_AUTO_CREATE_TOPICS_CONFIG, false
				),
				new StringDeserializer(),
				deserializer
		);
		factory.addListener(new MicrometerConsumerListener<>(meterRegistry));
		return factory;
	}

	@Bean
	public ConcurrentKafkaListenerContainerFactory<String, BinanceStreamResponse> kafkaListenerContainerFactory() {
		ConcurrentKafkaListenerContainerFactory<String, BinanceStreamResponse> factory = new ConcurrentKafkaListenerContainerFactory<>();
		factory.setConsumerFactory(consumerFactory());
		return factory;
	}
}
