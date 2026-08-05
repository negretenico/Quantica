package com.negretenico.quantica.markettransformer.validation;

public record OrderValidationResult(boolean accepted, String reason) {

	public static OrderValidationResult accept() {
		return new OrderValidationResult(true, null);
	}

	public static OrderValidationResult reject(String reason) {
		return new OrderValidationResult(false, reason);
	}
}
