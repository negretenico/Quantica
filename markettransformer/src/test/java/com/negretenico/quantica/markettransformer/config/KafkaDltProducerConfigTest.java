package com.negretenico.quantica.markettransformer.config;

import com.negretenico.quantica.markettransformer.model.KafkaProperties;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.kafka.core.KafkaTemplate;

import static org.junit.jupiter.api.Assertions.*;

@ExtendWith(MockitoExtension.class)
class KafkaDltProducerConfigTest {

	KafkaDltProducerConfig kafkaDltProducerConfig;

	@BeforeEach
	void setup() {
		KafkaProperties.ErrorHandler errorHandlerConfig = new KafkaProperties.ErrorHandler(1000L, 3);
		KafkaProperties kafkaProperties = new KafkaProperties("localhost:9092", "test-group", errorHandlerConfig);
		kafkaDltProducerConfig = new KafkaDltProducerConfig(kafkaProperties);
	}

	@Test
	void dltKafkaTemplateIsCreated() {
		KafkaTemplate<byte[], byte[]> template = kafkaDltProducerConfig.dltKafkaTemplate();
		assertNotNull(template);
	}

	@Test
	void dltProducerFactoryIsCreated() {
		assertNotNull(kafkaDltProducerConfig.dltProducerFactory());
	}
}
