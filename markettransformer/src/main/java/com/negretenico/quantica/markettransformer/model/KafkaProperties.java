package com.negretenico.quantica.markettransformer.model;

import org.springframework.boot.context.properties.ConfigurationProperties;

@ConfigurationProperties(prefix = "kafka")
public record KafkaProperties(String bootstrap, String groupId) {
}
