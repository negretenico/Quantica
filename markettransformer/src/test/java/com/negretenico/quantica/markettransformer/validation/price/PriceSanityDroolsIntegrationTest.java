package com.negretenico.quantica.markettransformer.validation.price;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.kie.api.KieBase;
import org.kie.api.io.ResourceType;
import org.kie.api.runtime.KieSession;
import org.kie.internal.utils.KieHelper;
import org.springframework.core.io.ClassPathResource;

import java.io.IOException;
import java.nio.charset.StandardCharsets;

import static org.junit.jupiter.api.Assertions.*;

class PriceSanityDroolsIntegrationTest {

	KieBase kieBase;
	TrailingPriceWindow window;

	@BeforeEach
	void setup() throws IOException {
		KieHelper kieHelper = new KieHelper();
		String drl = new ClassPathResource("rules/price-sanity.drl")
				.getContentAsString(StandardCharsets.UTF_8);
		kieHelper.addContent(drl, ResourceType.DRL);
		kieBase = kieHelper.build();
		window = new TrailingPriceWindow(new PriceSanityProperties(100, 5, 0.50));
	}

	private PriceCheckResult fireRules(String symbol, double price) {
		KieSession session = kieBase.newKieSession();
		try {
			session.setGlobal("window", window);
			session.insert(new PriceCheckFact(symbol, price, System.currentTimeMillis()));
			PriceCheckResult result = new PriceCheckResult();
			session.insert(result);
			session.fireAllRules();
			return result;
		} finally {
			session.dispose();
		}
	}

	@Test
	void ruleRejectsZeroPrice() {
		PriceCheckResult result = fireRules("BTCUSDT", 0.0);
		assertTrue(result.isRejected());
		assertEquals("non_positive", result.getRuleTag());
	}

	@Test
	void ruleRejectsNegativePrice() {
		PriceCheckResult result = fireRules("BTCUSDT", -5.0);
		assertTrue(result.isRejected());
		assertEquals("non_positive", result.getRuleTag());
	}

	@Test
	void ruleAcceptsDuringColdStart() {
		PriceCheckResult result = fireRules("BTCUSDT", 100.0);
		assertFalse(result.isRejected());
	}

	@Test
	void ruleRejectsHighMedianDeviation() {
		for (int i = 0; i < 5; i++) {
			window.addPrice("BTCUSDT", 100.0);
		}

		PriceCheckResult result = fireRules("BTCUSDT", 200.0);
		assertTrue(result.isRejected());
		assertEquals("median_deviation", result.getRuleTag());
	}

	@Test
	void ruleAcceptsWithinMedianDeviation() {
		for (int i = 0; i < 5; i++) {
			window.addPrice("BTCUSDT", 100.0);
		}

		PriceCheckResult result = fireRules("BTCUSDT", 120.0);
		assertFalse(result.isRejected());
	}

	@Test
	void salience100FiresBeforeSalience50() {
		PriceCheckResult result = fireRules("BTCUSDT", 0.0);
		assertTrue(result.isRejected());
		assertEquals("non_positive", result.getRuleTag());
	}

	@Test
	void ruleAcceptsAtExactThresholdBoundary() {
		for (int i = 0; i < 5; i++) {
			window.addPrice("BTCUSDT", 100.0);
		}

		PriceCheckResult result = fireRules("BTCUSDT", 150.0);
		assertFalse(result.isRejected());
	}

	@Test
	void ruleRejectsJustAboveThresholdBoundary() {
		for (int i = 0; i < 5; i++) {
			window.addPrice("BTCUSDT", 100.0);
		}

		PriceCheckResult result = fireRules("BTCUSDT", 150.01);
		assertTrue(result.isRejected());
		assertEquals("median_deviation", result.getRuleTag());
	}
}
