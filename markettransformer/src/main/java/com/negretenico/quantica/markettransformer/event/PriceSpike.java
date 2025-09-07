package com.negretenico.quantica.markettransformer.event;

import com.negretenico.quantica.markettransformer.model.BinanceStreamResponse;
import com.negretenico.quantica.markettransformer.model.SignalEventType;
import com.negretenico.quantica.markettransformer.model.events.OrderReceived;
import com.negretenico.quantica.markettransformer.model.events.SignalEvent;
import com.negretenico.quantica.markettransformer.stream.producer.KafkaPublisher;
import lombok.extern.slf4j.Slf4j;
import org.springframework.context.ApplicationListener;
import org.springframework.core.annotation.Order;
import org.springframework.stereotype.Service;

import java.math.BigDecimal;
import java.math.BigInteger;
import java.math.RoundingMode;
import java.util.LinkedList;
import java.util.Map;

@Service
@Slf4j
public class PriceSpike implements ApplicationListener<OrderReceived> {
	private final KafkaPublisher publisher;
	private final BigDecimal THRESHOLD = new BigDecimal("0.02"); // 2% move
	private final LinkedList<BigInteger> recentPrices = new LinkedList<>();

	public PriceSpike(KafkaPublisher publisher) {
		this.publisher = publisher;
	}

	@Override
	public void onApplicationEvent(OrderReceived event) {
		log.info("PriceSpike: Received event");
		BinanceStreamResponse order = event.getBinanceOrder();
		BigInteger price = order.getPriceAsBiInteger();
		if (recentPrices.isEmpty()) {
			recentPrices.add(price);
			return;
		}
		BigInteger lastPrice = recentPrices.getLast();
		BigDecimal priceDecimal = new BigDecimal(price);
		BigDecimal lastPriceDecimal = new BigDecimal(lastPrice);
		BigDecimal change = priceDecimal.subtract(lastPriceDecimal)
				.abs()
				.divide(lastPriceDecimal, 4, RoundingMode.DOWN);
		log.info("PriceSpike: Detected change of {}",change);
		if (change.compareTo(THRESHOLD) > 0) {
			log.info("PriceSpike: Anomaly detected publishing event");
			publisher.publish(new SignalEvent(
					order.symbol(),
					order.eventTime(),
					SignalEventType.PRICE_SPIKE,
					String.format("Price change %.2f%% exceeded threshold %.2f%%",
							change.multiply(new BigDecimal("100")), THRESHOLD.multiply(new BigDecimal("100"))),
					Double.parseDouble(order.price()),
					Double.parseDouble(order.quantity()),
					order.getTradeSide(),
					Map.of("priceChange", change, "threshold", THRESHOLD)
			));
		}
		recentPrices.add(price);
		if (recentPrices.size() > 100) {
			log.info("PriceSpike: Overflow removing oldest element");
			recentPrices.removeFirst();
		}
	}

}
