package com.negretenico.quantica.markettransformer.validation.price;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.*;

class TrailingPriceWindowTest {

	TrailingPriceWindow window;

	@BeforeEach
	void setup() {
		PriceSanityProperties properties = new PriceSanityProperties(5, 3, 0.50);
		window = new TrailingPriceWindow(properties);
	}

	@Test
	void addPriceStoresInWindow() {
		window.addPrice("BTCUSDT", 100.0);
		window.addPrice("BTCUSDT", 101.0);
		assertEquals(2, window.getCount("BTCUSDT"));
	}

	@Test
	void windowEvictsOldestWhenFull() {
		for (int i = 1; i <= 6; i++) {
			window.addPrice("BTCUSDT", i * 10.0);
		}
		assertEquals(5, window.getCount("BTCUSDT"));
		assertEquals(40.0, window.getMedian("BTCUSDT"));
	}

	@Test
	void medianOfOddCount() {
		window.addPrice("BTCUSDT", 10.0);
		window.addPrice("BTCUSDT", 30.0);
		window.addPrice("BTCUSDT", 20.0);
		assertEquals(20.0, window.getMedian("BTCUSDT"));
	}

	@Test
	void medianOfEvenCount() {
		window.addPrice("BTCUSDT", 10.0);
		window.addPrice("BTCUSDT", 20.0);
		window.addPrice("BTCUSDT", 30.0);
		window.addPrice("BTCUSDT", 40.0);
		assertEquals(25.0, window.getMedian("BTCUSDT"));
	}

	@Test
	void medianIsolatedBySymbol() {
		window.addPrice("BTCUSDT", 100.0);
		window.addPrice("ETHUSDT", 3000.0);
		assertEquals(100.0, window.getMedian("BTCUSDT"));
		assertEquals(3000.0, window.getMedian("ETHUSDT"));
	}

	@Test
	void coldStartReturnsTrueWhenBelowThreshold() {
		window.addPrice("BTCUSDT", 100.0);
		window.addPrice("BTCUSDT", 101.0);
		assertTrue(window.isColdStart("BTCUSDT"));
	}

	@Test
	void coldStartReturnsFalseWhenAtThreshold() {
		window.addPrice("BTCUSDT", 100.0);
		window.addPrice("BTCUSDT", 101.0);
		window.addPrice("BTCUSDT", 102.0);
		assertFalse(window.isColdStart("BTCUSDT"));
	}

	@Test
	void getMedianForUnknownSymbolReturnsZero() {
		assertEquals(0.0, window.getMedian("UNKNOWN"));
	}

	@Test
	void getCountForUnknownSymbolReturnsZero() {
		assertEquals(0, window.getCount("UNKNOWN"));
	}

	@Test
	void coldStartReturnsTrueForUnknownSymbol() {
		assertTrue(window.isColdStart("UNKNOWN"));
	}
}
