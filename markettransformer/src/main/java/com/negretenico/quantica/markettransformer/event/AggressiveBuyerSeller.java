package com.negretenico.quantica.markettransformer.event;

import com.negretenico.quantica.markettransformer.model.BinanceStreamResponse;
import com.negretenico.quantica.markettransformer.model.SignalEventType;
import com.negretenico.quantica.markettransformer.model.TradeIndicator;
import com.negretenico.quantica.markettransformer.model.events.OrderReceived;
import com.negretenico.quantica.markettransformer.model.events.SignalEvent;
import com.negretenico.quantica.markettransformer.stream.producer.SignalPublisher;
import io.micrometer.core.annotation.Timed;
import lombok.extern.slf4j.Slf4j;
import org.springframework.context.ApplicationListener;
import org.springframework.stereotype.Service;

import java.util.LinkedList;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.concurrent.ConcurrentHashMap;

@Service
@Slf4j
public class AggressiveBuyerSeller implements ApplicationListener<OrderReceived> {
	private final SignalPublisher publisher;
	private final ConcurrentHashMap<String, TradeIndicator> lastSideBySymbol = new ConcurrentHashMap<>();
	private final ConcurrentHashMap<String, List<TradeIndicator>> recentSidesBySymbol = new ConcurrentHashMap<>();
	private final ConcurrentHashMap<String, Integer> streakCountBySymbol = new ConcurrentHashMap<>();

	public AggressiveBuyerSeller(SignalPublisher publisher) {
		this.publisher = publisher;
	}

	@Override
	@Timed(value = "quantica.stage.detector", extraTags = {"detector", "aggressive_buyer_seller"})
	public void onApplicationEvent(OrderReceived event) {
		log.debug("AggressiveBuyerSeller: Received event");
		BinanceStreamResponse binanceStreamResponse = event.getBinanceOrder();
		String symbol = binanceStreamResponse.symbol();
		TradeIndicator side = binanceStreamResponse.getTradeSide();
		TradeIndicator lastSide = lastSideBySymbol.get(symbol);
		List<TradeIndicator> recentSides = recentSidesBySymbol.computeIfAbsent(symbol, k -> new LinkedList<>());
		int streakCount = streakCountBySymbol.getOrDefault(symbol, 0);
		if (Objects.isNull(lastSide) || !lastSide.equals(side)) {
			lastSideBySymbol.put(symbol, side);
			streakCount = 1;
		} else {
			streakCount++;
		}
		streakCountBySymbol.put(symbol, streakCount);
		recentSides.add(side);
		int STREAK_THRESHOLD = 5;
		if (recentSides.size() > STREAK_THRESHOLD) {
			recentSides.removeFirst();
		}
		if (streakCount < STREAK_THRESHOLD) {
			log.debug("DominantSideDetected: No side is dominating");
			return;
		}
		SignalEvent signalEvent = new SignalEvent(
				binanceStreamResponse.symbol(),
				binanceStreamResponse.eventTime(),
				SignalEventType.DOMINANT_SIDE,
				String.format("%s side dominated %d trades", side, streakCount),
				Double.parseDouble(binanceStreamResponse.price()),
				Double.parseDouble(binanceStreamResponse.quantity()),
				side,
				Map.of("streakCount", streakCount)
		);
		log.info("DominantSideDetected: {} side dominated {} trades in a row", side, streakCount);
		publisher.publish(signalEvent);
		streakCountBySymbol.put(symbol, 0);
	}
}
