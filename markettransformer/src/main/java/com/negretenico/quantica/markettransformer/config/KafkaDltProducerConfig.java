package com.negretenico.quantica.markettransformer.config;

import com.negretenico.quantica.markettransformer.model.KafkaProperties;
import org.apache.kafka.clients.producer.ProducerConfig;
import org.apache.kafka.common.serialization.ByteArraySerializer;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.kafka.core.DefaultKafkaProducerFactory;
import org.springframework.kafka.core.KafkaTemplate;
import org.springframework.kafka.core.ProducerFactory;

import java.util.Map;

@Configuration
public class KafkaDltProducerConfig {
	private final KafkaProperties kafkaProperties;

	public KafkaDltProducerConfig(KafkaProperties kafkaProperties) {
		this.kafkaProperties = kafkaProperties;
	}

	@Bean
	public ProducerFactory<byte[], byte[]> dltProducerFactory() {
		return new DefaultKafkaProducerFactory<>(
				Map.of(
						ProducerConfig.BOOTSTRAP_SERVERS_CONFIG, kafkaProperties.bootstrap(),
						ProducerConfig.KEY_SERIALIZER_CLASS_CONFIG, ByteArraySerializer.class,
						ProducerConfig.VALUE_SERIALIZER_CLASS_CONFIG, ByteArraySerializer.class
				)
		);
	}

	@Bean
	public KafkaTemplate<byte[], byte[]> dltKafkaTemplate() {
		return new KafkaTemplate<>(dltProducerFactory());
	}
}
