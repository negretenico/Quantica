package com.negretenico.quantica.marketListener.config;

import org.springframework.boot.context.properties.ConfigurationProperties;

@ConfigurationProperties(prefix = "binance.stream")
public record BinanceStreamProperties(String base, String symbols, long reconnectDelaySeconds) {
}
