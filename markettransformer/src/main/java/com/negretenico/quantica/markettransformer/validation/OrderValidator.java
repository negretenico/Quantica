package com.negretenico.quantica.markettransformer.validation;

import com.negretenico.quantica.markettransformer.model.BinanceStreamResponse;

public interface OrderValidator {

	OrderValidationResult validate(BinanceStreamResponse order, ValidationChain chain);
}
