package com.negretenico.quantica.markettransformer.event;

import com.common.functionico.evaluation.Result;
import com.negretenico.quantica.markettransformer.model.BinanceStreamResponse;
import com.negretenico.quantica.markettransformer.model.SignalEventType;
import com.negretenico.quantica.markettransformer.model.events.OrderReceived;
import com.negretenico.quantica.markettransformer.model.events.SignalEvent;
import com.negretenico.quantica.markettransformer.stream.producer.KafkaPublisher;
import lombok.extern.slf4j.Slf4j;
import org.springframework.context.ApplicationListener;
import org.springframework.stereotype.Component;

import java.math.BigInteger;
import java.util.Map;


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
		BigInteger quantity =
				Result.of(order::getQuantityAsBigInteger).getOrElse(BigInteger.ZERO);
		if(quantity.compareTo(MILLION)<=0){
			log.info("LargeTradeDetected: Order {}, did not meet threshold",
					order.getId());
			return;
		}
		log.info("LargeTradeDetected: Anomaly detected publishing event");
		publisher.publish(new SignalEvent(
				order.symbol(),
				order.eventTime(),
				SignalEventType.LARGE_TRADE,
				String.format("Quantity %s exceeded threshold %s", order.quantity(), MILLION),
				Double.parseDouble(order.price()),
				Double.parseDouble(order.quantity()),
				order.getTradeSide(),
				Map.of("threshold", MILLION)
		));
	}
}
