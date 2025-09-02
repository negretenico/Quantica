package com.negretenico.quantica.marketListener.config;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.negretenico.quantica.marketListener.binance.BinanceWssHandler;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.ApplicationEventPublisher;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.web.socket.client.WebSocketClient;
import org.springframework.web.socket.client.WebSocketConnectionManager;
import org.springframework.web.socket.client.standard.StandardWebSocketClient;
import org.springframework.web.socket.config.annotation.EnableWebSocket;
import org.springframework.web.socket.handler.TextWebSocketHandler;

@Configuration
@EnableWebSocket
public class WebsocketConfig {
	@Bean
	public WebSocketConnectionManager webSocketConnectionManager(@Value("$" +
																																	 "{binance.stream" +
																																	 "}") String streamUrl,
																															 ApplicationEventPublisher eventPublisher) {
		WebSocketConnectionManager manager = new WebSocketConnectionManager(
				client(),
				binanceWebsocketHandler(eventPublisher),
				streamUrl
		);
		manager.setAutoStartup(true);
		return manager;
	}

	@Bean
	public WebSocketClient client() {
		return new StandardWebSocketClient();
	}

	@Bean
	public TextWebSocketHandler binanceWebsocketHandler(ApplicationEventPublisher applicationEventPublisher) {
		return new BinanceWssHandler(new ObjectMapper(), applicationEventPublisher);
	}
}
