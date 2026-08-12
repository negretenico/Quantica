package com.negretenico.quantica.markettransformer.config;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.negretenico.quantica.markettransformer.model.KafkaProperties;
import io.micrometer.core.instrument.simple.SimpleMeterRegistry;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.kafka.config.ConcurrentKafkaListenerContainerFactory;
import org.springframework.kafka.core.KafkaTemplate;
import org.springframework.kafka.listener.DefaultErrorHandler;

import static org.junit.jupiter.api.Assertions.*;

@ExtendWith(MockitoExtension.class)
class KafkaConsumerConfigTest {
	@Mock
	KafkaTemplate<byte[], byte[]> dltKafkaTemplate;

	KafkaConsumerConfig kafkaConsumerConfig;

	@BeforeEach
	void setup() {
		KafkaProperties.ErrorHandler errorHandlerConfig = new KafkaProperties.ErrorHandler(1000L, 3);
		KafkaProperties kafkaProperties = new KafkaProperties("localhost:9092", "test-group", errorHandlerConfig);
		kafkaConsumerConfig = new KafkaConsumerConfig(kafkaProperties, new ObjectMapper(), new SimpleMeterRegistry(), dltKafkaTemplate);
	}

	@Test
	void kafkaErrorHandlerIsDefaultErrorHandler() {
		DefaultErrorHandler errorHandler = kafkaConsumerConfig.kafkaErrorHandler();
		assertNotNull(errorHandler);
		assertInstanceOf(DefaultErrorHandler.class, errorHandler);
	}

	@Test
	void containerFactoryHasErrorHandler() {
		ConcurrentKafkaListenerContainerFactory<?, ?> factory = kafkaConsumerConfig.kafkaListenerContainerFactory();
		assertNotNull(factory);
	}
}
