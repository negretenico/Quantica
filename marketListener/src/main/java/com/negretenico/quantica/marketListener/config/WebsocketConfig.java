package com.negretenico.quantica.marketListener.config;

import com.negretenico.quantica.marketListener.binance.BinanceWssHandler;
import io.micrometer.core.aop.TimedAspect;
import io.micrometer.core.instrument.MeterRegistry;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.web.socket.client.WebSocketClient;
import org.springframework.web.socket.client.WebSocketConnectionManager;
import org.springframework.web.socket.client.standard.StandardWebSocketClient;
import org.springframework.web.socket.config.annotation.EnableWebSocket;

@Configuration
@EnableWebSocket
public class WebsocketConfig {

	@Bean
	public TimedAspect timedAspect(MeterRegistry registry) {
		return new TimedAspect(registry);
	}

	@Bean
	public WebSocketConnectionManager webSocketConnectionManager(@Value("${binance.stream}") String streamUrl,
																															 BinanceWssHandler binanceWssHandler) {
		WebSocketConnectionManager manager = new WebSocketConnectionManager(
				client(),
				binanceWssHandler,
				streamUrl
		);
		manager.setAutoStartup(true);
		return manager;
	}

	@Bean
	public WebSocketClient client() {
		return new StandardWebSocketClient();
	}
}
