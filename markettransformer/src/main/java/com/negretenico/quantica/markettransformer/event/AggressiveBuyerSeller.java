package com.negretenico.quantica.markettransformer.event;

import com.negretenico.quantica.markettransformer.model.BinanceStreamResponse;
import com.negretenico.quantica.markettransformer.model.TradeIndicator;
import com.negretenico.quantica.markettransformer.model.events.OrderReceived;
import com.negretenico.quantica.markettransformer.stream.producer.KafkaPublisher;
import lombok.extern.slf4j.Slf4j;
import org.springframework.context.ApplicationListener;
import org.springframework.stereotype.Service;

import java.util.LinkedList;
import java.util.List;
import java.util.Objects;

@Service
@Slf4j
public class AggressiveBuyerSeller  implements ApplicationListener<OrderReceived> {
	private final KafkaPublisher publisher;
	private  TradeIndicator lastSide=null;
	private final List<TradeIndicator> recentSides = new LinkedList<>();
	private  int streakCount=0;
	public AggressiveBuyerSeller(KafkaPublisher publisher) {
		this.publisher = publisher;
	}

	@Override
	public void onApplicationEvent(OrderReceived event) {
		log.info("AggressiveBuyerSeller: Received event");
		BinanceStreamResponse binanceStreamResponse = event.getBinanceOrder();
		TradeIndicator side=binanceStreamResponse.getTradeSide();
		if (Objects.isNull(lastSide) || !lastSide.equals(side)) {
			lastSide = side;
			streakCount = 1;
		} else {
			streakCount++;
		}
		recentSides.add(side);
		int STREAK_THRESHOLD = 5;
		if (recentSides.size() > STREAK_THRESHOLD) {
			recentSides.removeFirst();
		}
		if (streakCount < STREAK_THRESHOLD) {
			log.info("DominantSideDetected: No side is dominating");
			return;
		}
		log.info("DominantSideDetected: {} side dominated {} trades in a row", side, streakCount);
		publisher.publish(binanceStreamResponse);
		streakCount = 0;
	}
}
