package com.negretenico.quantica.markettransformer.event;

import com.negretenico.quantica.markettransformer.model.BinanceStreamResponse;
import com.negretenico.quantica.markettransformer.model.events.OrderReceived;
import com.negretenico.quantica.markettransformer.stream.producer.KafkaPublisher;
import lombok.extern.slf4j.Slf4j;
import org.springframework.context.ApplicationListener;
import org.springframework.stereotype.Component;

import java.math.BigInteger;


@Slf4j
@Component
public class LargeTradeDetected implements ApplicationListener<OrderReceived> {
	private final KafkaPublisher publisher;
	private final BigInteger MILLION = new BigInteger("1000000");
	public LargeTradeDetected(KafkaPublisher publisher) {
		this.publisher = publisher;
	}

	@Override
	public void onApplicationEvent(OrderReceived event) {
		log.info("LargeTradeDetected: Received event");
		BinanceStreamResponse order = event.getBinanceOrder();
		BigInteger quantity = order.getQuantityAsBigInteger();
		if(quantity.compareTo(MILLION)<=0){
			log.info("LargeTradeDetected: Order {}, did not meet threshold",
					order.getId());
			return;
		}
		log.info("LargeTradeDetected: Anomaly detected publishing event");
		publisher.publish(order);
	}
}
