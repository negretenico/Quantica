package com.negretenico.quantica.markettransformer.validation;

import com.negretenico.quantica.markettransformer.model.BinanceStreamResponse;

import java.util.ArrayList;
import java.util.List;

public class ValidationChain {

	private final List<OrderValidator> validators;
	private int currentIndex;

	private ValidationChain(List<OrderValidator> validators, int currentIndex) {
		this.validators = validators;
		this.currentIndex = currentIndex;
	}

	public static Builder start() {
		return new Builder();
	}

	public OrderValidationResult execute(BinanceStreamResponse order) {
		ValidationChain fresh = new ValidationChain(validators, 0);
		return fresh.next(order);
	}

	public OrderValidationResult next(BinanceStreamResponse order) {
		if (currentIndex >= validators.size()) {
			return OrderValidationResult.accept();
		}
		OrderValidator validator = validators.get(currentIndex);
		currentIndex++;
		return validator.validate(order, this);
	}

	public static class Builder {
		private final List<OrderValidator> validators = new ArrayList<>();

		public Builder then(OrderValidator validator) {
			validators.add(validator);
			return this;
		}

		public ValidationChain build() {
			return new ValidationChain(List.copyOf(validators), 0);
		}
	}
}
