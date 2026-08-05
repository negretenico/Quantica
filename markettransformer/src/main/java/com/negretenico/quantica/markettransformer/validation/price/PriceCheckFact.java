package com.negretenico.quantica.markettransformer.validation.price;

public record PriceCheckFact(String symbol, double price, long eventTime) {
}
