package com.negretenico.quantica.markettransformer.validation.price;

import com.negretenico.quantica.markettransformer.model.BinanceStreamResponse;
import com.negretenico.quantica.markettransformer.validation.OrderValidationResult;
import com.negretenico.quantica.markettransformer.validation.ValidationChain;
import io.micrometer.core.instrument.simple.SimpleMeterRegistry;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.kie.api.KieBase;
import org.kie.api.io.ResourceType;
import org.kie.internal.utils.KieHelper;
import org.springframework.core.io.ClassPathResource;

import java.io.IOException;
import java.nio.charset.StandardCharsets;

import static org.junit.jupiter.api.Assertions.*;

class PriceSanityGateTest {

	SimpleMeterRegistry registry;
	TrailingPriceWindow window;
	PriceSanityGate gate;
	ValidationChain chain;

	@BeforeEach
	void setup() throws IOException {
		registry = new SimpleMeterRegistry();
		window = new TrailingPriceWindow(new PriceSanityProperties(100, 5, 0.50));
		KieHelper kieHelper = new KieHelper();
		String drl = new ClassPathResource("rules/price-sanity.drl")
				.getContentAsString(StandardCharsets.UTF_8);
		kieHelper.addContent(drl, ResourceType.DRL);
		KieBase kieBase = kieHelper.build();
		gate = new PriceSanityGate(kieBase, window, registry);
		chain = ValidationChain.start().then(gate).build();
	}

	private BinanceStreamResponse order(String symbol, String price) {
		return new BinanceStreamResponse("trade", System.currentTimeMillis(), System.currentTimeMillis(),
				symbol, 1L, price, "0.01", "MARKET", false);
	}

	@Test
	void rejectsNonPositivePrice() {
		OrderValidationResult result = chain.execute(order("BTCUSDT", "0.0"));
		assertFalse(result.accepted());
		assertTrue(result.reason().contains("non-positive"));
	}

	@Test
	void acceptsDuringColdStart() {
		OrderValidationResult result = chain.execute(order("BTCUSDT", "100.0"));
		assertTrue(result.accepted());
		assertEquals(1, window.getCount("BTCUSDT"));
	}

	@Test
	void rejectsMedianDeviationAboveThreshold() {
		for (int i = 0; i < 5; i++) {
			window.addPrice("BTCUSDT", 100.0);
		}

		OrderValidationResult result = chain.execute(order("BTCUSDT", "200.0"));
		assertFalse(result.accepted());
	}

	@Test
	void acceptsPriceWithinMedianThreshold() {
		for (int i = 0; i < 5; i++) {
			window.addPrice("BTCUSDT", 100.0);
		}

		OrderValidationResult result = chain.execute(order("BTCUSDT", "120.0"));
		assertTrue(result.accepted());
		assertEquals(6, window.getCount("BTCUSDT"));
	}

	@Test
	void rejectedPriceNotAddedToWindow() {
		for (int i = 0; i < 5; i++) {
			window.addPrice("BTCUSDT", 100.0);
		}

		chain.execute(order("BTCUSDT", "200.0"));
		assertEquals(5, window.getCount("BTCUSDT"));
	}

	@Test
	void incrementsAcceptedCounterOnAccept() {
		chain.execute(order("BTCUSDT", "100.0"));
		assertEquals(1.0, registry.counter("quantica.validation.price.accepted").count());
	}

	@Test
	void incrementsRejectedCounterOnReject() {
		chain.execute(order("BTCUSDT", "0.0"));
		assertEquals(1.0, registry.counter("quantica.validation.price.rejected", "symbol", "BTCUSDT", "rule", "non_positive").count());
	}

	@Test
	void evaluationTimerRecords() {
		chain.execute(order("BTCUSDT", "100.0"));
		assertEquals(1, registry.timer("quantica.validation.price.evaluation.duration").count());
	}
}
