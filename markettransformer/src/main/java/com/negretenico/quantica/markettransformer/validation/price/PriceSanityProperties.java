package com.negretenico.quantica.markettransformer.validation.price;

import org.springframework.boot.context.properties.ConfigurationProperties;

@ConfigurationProperties(prefix = "price.sanity")
public record PriceSanityProperties(int windowSize, int bootstrapThreshold, double deviationThreshold) {
}
