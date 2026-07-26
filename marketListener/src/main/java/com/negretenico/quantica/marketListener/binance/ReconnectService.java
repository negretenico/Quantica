package com.negretenico.quantica.marketListener.binance;

import com.negretenico.quantica.marketListener.config.BinanceStreamProperties;
import com.negretenico.quantica.marketListener.model.events.WssDisconnected;
import lombok.extern.slf4j.Slf4j;
import org.springframework.context.ApplicationListener;
import org.springframework.stereotype.Component;
import org.springframework.web.socket.client.WebSocketConnectionManager;

import java.util.concurrent.Executors;
import java.util.concurrent.ScheduledExecutorService;
import java.util.concurrent.TimeUnit;

@Slf4j
@Component
public class ReconnectService implements ApplicationListener<WssDisconnected> {
	private final WebSocketConnectionManager manager;
	private final long reconnectDelaySeconds;
	private final ScheduledExecutorService scheduler = Executors.newSingleThreadScheduledExecutor();

	public ReconnectService(WebSocketConnectionManager manager, BinanceStreamProperties properties) {
		this.manager = manager;
		this.reconnectDelaySeconds = properties.reconnectDelaySeconds();
	}

	@Override
	public void onApplicationEvent(WssDisconnected event) {
		scheduleReconnect(reconnectDelaySeconds);
	}

	private void scheduleReconnect(long delaySeconds) {
		log.info("Scheduling reconnect in {}s", delaySeconds);
		scheduler.schedule(() -> {
			try {
				manager.stop();
				manager.start();
				log.info("Reconnect initiated");
			} catch (Exception e) {
				log.error("Reconnect attempt failed — retrying in {}s", delaySeconds, e);
				scheduleReconnect(delaySeconds);
			}
		}, delaySeconds, TimeUnit.SECONDS);
	}
}
