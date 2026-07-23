package com.negretenico.quantica.marketListener.config;

import org.springframework.boot.context.properties.ConfigurationProperties;

@ConfigurationProperties(prefix = "kafka")
public record KafkaProperties(String bootstrap, String orderTopic, int orderTopicPartitions, short orderTopicReplicationFactor) {
}
