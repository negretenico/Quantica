package com.negretenico.quantica.markettransformer.stream.consumer;

import com.negretenico.quantica.markettransformer.model.BinanceStreamResponse;
import org.apache.kafka.clients.consumer.ConsumerRecord;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.Mockito;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.context.ApplicationEventPublisher;

import static org.junit.jupiter.api.Assertions.*;
@ExtendWith(MockitoExtension.class)
class OrderConsumerTest {
	@Mock
	ApplicationEventPublisher applicationEventPublisher;
	@Mock
	ConsumerRecord<String, BinanceStreamResponse> record;
	@Mock
			BinanceStreamResponse response;
	OrderConsumer orderConsumer;

	@BeforeEach
	void setup(){
		orderConsumer=new OrderConsumer(applicationEventPublisher);
	}
	@Test
	void consumerMessage(){
		Mockito.when(record.value()).thenReturn(response);
		Mockito.doNothing().when(applicationEventPublisher).publishEvent(Mockito.any());
		orderConsumer.consumeOrder(record);
		Mockito.verify(applicationEventPublisher,Mockito.atLeastOnce()).publishEvent(Mockito.any());

	}

}