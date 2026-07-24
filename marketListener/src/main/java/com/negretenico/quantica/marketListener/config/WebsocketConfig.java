package com.negretenico.quantica.marketListener.config;

import com.negretenico.quantica.marketListener.binance.BinanceWssHandler;
import io.micrometer.core.aop.TimedAspect;
import io.micrometer.core.instrument.MeterRegistry;
import org.springframework.boot.context.properties.EnableConfigurationProperties;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.web.socket.client.WebSocketClient;
import org.springframework.web.socket.client.WebSocketConnectionManager;
import org.springframework.web.socket.client.standard.StandardWebSocketClient;
import org.springframework.web.socket.config.annotation.EnableWebSocket;

@Configuration
@EnableWebSocket
@EnableConfigurationProperties(BinanceStreamProperties.class)
public class WebsocketConfig {

	@Bean
	public TimedAspect timedAspect(MeterRegistry registry) {
		return new TimedAspect(registry);
	}

	@Bean
	public WebSocketConnectionManager webSocketConnectionManager(BinanceStreamProperties streamProperties,
																 BinanceWssHandler binanceWssHandler) {
		String streamUrl = streamProperties.base() + "/" + streamProperties.symbols().replace(",", "/");
		WebSocketConnectionManager manager = new WebSocketConnectionManager(
				client(),
				binanceWssHandler,
				streamUrl
		);
		manager.setAutoStartup(true);
		manager.setAutoReconnect(true);
		return manager;
	}

	@Bean
	public WebSocketClient client() {
		return new StandardWebSocketClient();
	}
}
