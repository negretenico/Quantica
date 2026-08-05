package com.negretenico.quantica.markettransformer.validation.price;

import org.springframework.stereotype.Component;

import java.util.ArrayList;
import java.util.Collections;
import java.util.LinkedList;
import java.util.List;
import java.util.concurrent.ConcurrentHashMap;

@Component
public class TrailingPriceWindow {

	private final ConcurrentHashMap<String, LinkedList<Double>> windows = new ConcurrentHashMap<>();
	private final int windowSize;
	private final int bootstrapThreshold;
	private final double deviationThreshold;

	public TrailingPriceWindow(PriceSanityProperties properties) {
		this.windowSize = properties.windowSize();
		this.bootstrapThreshold = properties.bootstrapThreshold();
		this.deviationThreshold = properties.deviationThreshold();
	}

	public void addPrice(String symbol, double price) {
		windows.compute(symbol, (key, window) -> {
			if (window == null) {
				window = new LinkedList<>();
			}
			window.addLast(price);
			if (window.size() > windowSize) {
				window.removeFirst();
			}
			return window;
		});
	}

	public double getMedian(String symbol) {
		LinkedList<Double> window = windows.get(symbol);
		if (window == null || window.isEmpty()) {
			return 0.0;
		}
		List<Double> sorted = new ArrayList<>(window);
		Collections.sort(sorted);
		int size = sorted.size();
		if (size % 2 == 1) {
			return sorted.get(size / 2);
		}
		return (sorted.get(size / 2 - 1) + sorted.get(size / 2)) / 2.0;
	}

	public int getCount(String symbol) {
		LinkedList<Double> window = windows.get(symbol);
		return window == null ? 0 : window.size();
	}

	public boolean isColdStart(String symbol) {
		return getCount(symbol) < bootstrapThreshold;
	}

	public double getDeviationThreshold() {
		return deviationThreshold;
	}

	public int getBootstrapThreshold() {
		return bootstrapThreshold;
	}
}
