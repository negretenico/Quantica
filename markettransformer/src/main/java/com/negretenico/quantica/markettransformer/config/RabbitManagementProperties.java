package com.negretenico.quantica.markettransformer.config;

import org.springframework.boot.context.properties.ConfigurationProperties;

@ConfigurationProperties(prefix = "rabbitmq.management")
public record RabbitManagementProperties(String url) {}
