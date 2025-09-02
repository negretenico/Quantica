package com.negretenico.quantica.markettransformer.config;

import com.negretenico.quantica.markettransformer.model.KafkaProperties;
import org.apache.kafka.common.serialization.StringSerializer;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.kafka.config.ConcurrentKafkaListenerContainerFactory;
import org.springframework.kafka.core.ConsumerFactory;
import org.springframework.kafka.core.DefaultKafkaConsumerFactory;
import org.springframework.kafka.support.serializer.JsonSerializer;
import org.apache.kafka.clients.consumer.ConsumerConfig;
import java.util.Map;

@Configuration
public class KafkaConsumerConfig {
	private final KafkaProperties kafkaProperties;

	public KafkaConsumerConfig(KafkaProperties kafkaProperties) {
		this.kafkaProperties = kafkaProperties;
	}

	@Bean
	public ConsumerFactory<String, String> consumerFactory() {
		return new DefaultKafkaConsumerFactory<>(Map.of(
				ConsumerConfig.BOOTSTRAP_SERVERS_CONFIG, kafkaProperties.bootstrap(),
				ConsumerConfig.GROUP_ID_CONFIG, kafkaProperties.groupId(),
				ConsumerConfig.KEY_DESERIALIZER_CLASS_CONFIG, StringSerializer.class,
				ConsumerConfig.VALUE_DESERIALIZER_CLASS_CONFIG, JsonSerializer.class
				));
	}

	@Bean
	public ConcurrentKafkaListenerContainerFactory<String, String> kafkaListenerContainerFactory() {
		ConcurrentKafkaListenerContainerFactory<String, String> factory = new ConcurrentKafkaListenerContainerFactory<>();
		factory.setConsumerFactory(consumerFactory());
		return factory;
	}
}