package com.negretenico.quantica.marketListener.binance;

import com.common.functionico.evaluation.Result;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.negretenico.quantica.marketListener.model.BinanceStreamResponse;
import com.negretenico.quantica.marketListener.model.events.BinanceOrderReceived;
import lombok.extern.slf4j.Slf4j;
import org.springframework.context.ApplicationEventPublisher;
import org.springframework.web.socket.TextMessage;
import org.springframework.web.socket.WebSocketSession;
import org.springframework.web.socket.handler.TextWebSocketHandler;


@Slf4j
public class BinanceWssHandler extends TextWebSocketHandler {
	ObjectMapper objectMapper;
	WebSocketSession session;
	// TODO: create service to publish events
	ApplicationEventPublisher applicationEventPublisher;

	public BinanceWssHandler(ObjectMapper objectMapper,
													 ApplicationEventPublisher applicationEventPublisher) {
		this.objectMapper = objectMapper;
		this.applicationEventPublisher = applicationEventPublisher;
	}

	@Override
	public void afterConnectionEstablished(WebSocketSession session) {
		this.session = session;
		log.info("Connected to Binance WebSocket");
	}

	@Override
	public void handleTextMessage(WebSocketSession session, TextMessage message) {
		this.session = session;
		log.info("Received message: {}", message.getPayload());
		Result.of(() -> objectMapper.readValue(message.getPayload(), BinanceStreamResponse.class))
				.onSuccess(bsr -> {
					log.info("Successfully serialized msg, {}", bsr);
					log.info("Publishing msg, {}", bsr);
					applicationEventPublisher.publishEvent(BinanceOrderReceived.of(this, bsr));
					log.info("Published msg, {}", bsr);
				})
				.onFailure(e -> log.error("Error parsing message", e));
	}

	@Override
	public void handleTransportError(WebSocketSession session, Throwable exception) {
		log.error("WebSocket transport error", exception);
	}
}
