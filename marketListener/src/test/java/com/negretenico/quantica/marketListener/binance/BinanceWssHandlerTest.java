package com.negretenico.quantica.marketListener.binance;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.negretenico.quantica.marketListener.model.BinanceStreamResponse;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.Mockito;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.context.ApplicationEventPublisher;
import org.springframework.web.socket.TextMessage;
import org.springframework.web.socket.WebSocketSession;


@ExtendWith(MockitoExtension.class)
class BinanceWssHandlerTest {
	@Mock
	ApplicationEventPublisher publisher;
	@Mock
	WebSocketSession session;
	@Mock
	ObjectMapper mapper;
	@Mock
	TextMessage textMessage;
	@Mock
	BinanceStreamResponse binanceStreamResponse;
	BinanceWssHandler binanceWssHandler;

	@BeforeEach
	void setup() {
		binanceWssHandler = new BinanceWssHandler(mapper, publisher);
	}


	@Test
	void givenTheWebsocketMessageIsInvalidTHenIShouldCatchTheErrorAndNotPublishABinanceOrderReceivedEvent() throws JsonProcessingException {
		Mockito.when(textMessage.getPayload()).thenReturn("MSG");
		Mockito.when(mapper.readValue(Mockito.anyString(), Mockito.any(Class.class))).thenThrow(new RuntimeException(
				"THIS" +
						" IS " +
						"AN EXCEPTION"));
		binanceWssHandler.handleTextMessage(session, textMessage);
		Mockito.verify(publisher, Mockito.never()).publishEvent(Mockito.any());
	}

	@Test
	void givenTheWebsocketMessageIsValidThenIShouldPublishABinanceOrderReceivedEvent() throws JsonProcessingException {
		Mockito.when(textMessage.getPayload()).thenReturn("MSG");
		Mockito.when(mapper.readValue(Mockito.anyString(), Mockito.any(Class.class)))
				.thenReturn(binanceStreamResponse);
		binanceWssHandler.handleTextMessage(session, textMessage);
		Mockito.verify(publisher, Mockito.atLeastOnce()).publishEvent(Mockito.any());
	}

	@Test
	void afterConnectionEstablished() {
		binanceWssHandler.afterConnectionEstablished(session);
	}

	@Test
	void handleTransportError() {
		binanceWssHandler.handleTransportError(session, new Throwable());
	}
}