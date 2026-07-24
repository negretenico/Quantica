package com.negretenico.quantica.marketListener.binance;

import com.common.functionico.evaluation.Result;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.negretenico.quantica.marketListener.model.BinanceStreamResponse;
import com.negretenico.quantica.marketListener.model.events.BinanceOrderReceived;
import com.negretenico.quantica.marketListener.model.events.WssDisconnected;
import io.micrometer.core.instrument.MeterRegistry;
import io.micrometer.core.instrument.Timer;
import lombok.extern.slf4j.Slf4j;
import org.springframework.context.ApplicationEventPublisher;
import org.springframework.stereotype.Component;
import org.springframework.web.socket.CloseStatus;
import org.springframework.web.socket.TextMessage;
import org.springframework.web.socket.WebSocketSession;
import org.springframework.web.socket.handler.TextWebSocketHandler;


@Slf4j
@Component
public class BinanceWssHandler extends TextWebSocketHandler {
	private final ObjectMapper objectMapper;
	private final ApplicationEventPublisher applicationEventPublisher;
	private final Timer receiveTimer;
	private WebSocketSession session;

	public BinanceWssHandler(ObjectMapper objectMapper,
													 ApplicationEventPublisher applicationEventPublisher,
													 MeterRegistry meterRegistry) {
		this.objectMapper = objectMapper;
		this.applicationEventPublisher = applicationEventPublisher;
		this.receiveTimer = Timer.builder("quantica.stage.wss.receive")
				.register(meterRegistry);
	}

	@Override
	public void afterConnectionEstablished(WebSocketSession session) {
		this.session = session;
		log.info("Connected to Binance WebSocket");
	}

	@Override
	public void handleTextMessage(WebSocketSession session, TextMessage message) {
		Timer.Sample sample = Timer.start();
		this.session = session;
		log.debug("Received message: {}", message.getPayload());
		Result.of(() -> objectMapper.readValue(message.getPayload(), BinanceStreamResponse.class))
				.onSuccess(bsr -> {
					log.debug("Publishing msg: {}", bsr.getId());
					applicationEventPublisher.publishEvent(BinanceOrderReceived.of(this, bsr));
				})
				.onFailure(e -> log.error("Error parsing message", e));
		sample.stop(receiveTimer);
	}

	@Override
	public void afterConnectionClosed(WebSocketSession session, CloseStatus status) {
		log.warn("WebSocket connection closed: {}", status);
		applicationEventPublisher.publishEvent(new WssDisconnected(this));
	}

	@Override
	public void handleTransportError(WebSocketSession session, Throwable exception) {
		log.error("WebSocket transport error", exception);
	}
}
