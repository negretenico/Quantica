package com.negretenico.quantica.markettransformer.config;

import lombok.extern.slf4j.Slf4j;
import org.springframework.boot.web.embedded.tomcat.TomcatServletWebServerFactory;
import org.springframework.boot.web.server.WebServerFactoryCustomizer;
import org.springframework.stereotype.Component;

import java.net.ServerSocket;

@Component
@Slf4j
public class DynamicPortCustomizer implements WebServerFactoryCustomizer<TomcatServletWebServerFactory> {

	private static final int START_PORT = 8080;

	@Override
	public void customize(TomcatServletWebServerFactory factory) {
		int port = findAvailablePort();
		factory.setPort(port);
		log.info("Starting Spring Boot on port: {}" , port);
	}

	private int findAvailablePort() {
		int port = DynamicPortCustomizer.START_PORT;
		while (!isPortAvailable(port)) {
			port++;
		}
		return port;
	}

	private boolean isPortAvailable(int port) {
		try (ServerSocket socket = new ServerSocket(port)) {
			socket.setReuseAddress(true);
			return true;
		} catch (Exception e) {
			return false;
		}
	}
}
