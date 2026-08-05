package com.negretenico.quantica.markettransformer.validation.price;

public class PriceCheckResult {

	private boolean rejected;
	private String reason;
	private String ruleTag;

	public boolean isRejected() {
		return rejected;
	}

	public String getReason() {
		return reason;
	}

	public String getRuleTag() {
		return ruleTag;
	}

	public void reject(String ruleTag, String reason) {
		this.rejected = true;
		this.ruleTag = ruleTag;
		this.reason = reason;
	}
}
