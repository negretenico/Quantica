package com.negretenico.quantica.markettransformer.validation.price;

import com.negretenico.quantica.markettransformer.model.BinanceStreamResponse;
import com.negretenico.quantica.markettransformer.validation.OrderValidationResult;
import com.negretenico.quantica.markettransformer.validation.OrderValidator;
import com.negretenico.quantica.markettransformer.validation.ValidationChain;
import io.micrometer.core.instrument.Counter;
import io.micrometer.core.instrument.MeterRegistry;
import io.micrometer.core.instrument.Timer;
import lombok.extern.slf4j.Slf4j;
import org.kie.api.KieBase;
import org.kie.api.runtime.KieSession;
import org.springframework.stereotype.Component;

import java.util.Set;
import java.util.concurrent.ConcurrentHashMap;

@Slf4j
@Component
public class PriceSanityGate implements OrderValidator {

	private final KieBase kieBase;
	private final TrailingPriceWindow trailingPriceWindow;
	private final MeterRegistry meterRegistry;
	private final Counter acceptedCounter;
	private final Timer evaluationTimer;
	private final ConcurrentHashMap<String, Counter> rejectedCounters = new ConcurrentHashMap<>();
	private final Set<String> loggedRejections = ConcurrentHashMap.newKeySet();

	public PriceSanityGate(KieBase priceSanityKieBase, TrailingPriceWindow trailingPriceWindow, MeterRegistry meterRegistry) {
		this.kieBase = priceSanityKieBase;
		this.trailingPriceWindow = trailingPriceWindow;
		this.meterRegistry = meterRegistry;
		this.acceptedCounter = Counter.builder("quantica.validation.price.accepted")
				.register(meterRegistry);
		this.evaluationTimer = Timer.builder("quantica.validation.price.evaluation.duration")
				.register(meterRegistry);
	}

	@Override
	public OrderValidationResult validate(BinanceStreamResponse order, ValidationChain chain) {
		return evaluationTimer.record(() -> {
			double price = Double.parseDouble(order.price());
			PriceCheckFact fact = new PriceCheckFact(order.symbol(), price, order.eventTime());
			PriceCheckResult result = new PriceCheckResult();

			KieSession session = kieBase.newKieSession();
			try {
				session.setGlobal("window", trailingPriceWindow);
				session.insert(fact);
				session.insert(result);
				session.fireAllRules();
			} finally {
				session.dispose();
			}

			if (result.isRejected()) {
				rejectedCounters.computeIfAbsent(order.symbol() + "|" + result.getRuleTag(), key ->
						Counter.builder("quantica.validation.price.rejected")
								.tag("symbol", order.symbol())
								.tag("rule", result.getRuleTag())
								.register(meterRegistry))
						.increment();

				String logKey = order.symbol() + "|" + result.getRuleTag();
				if (loggedRejections.add(logKey)) {
					log.warn("Price sanity REJECTED -- symbol={} price={} rule={} reason={} (further duplicates suppressed)",
							order.symbol(), order.price(), result.getRuleTag(), result.getReason());
				}
				return OrderValidationResult.reject(result.getReason());
			}

			trailingPriceWindow.addPrice(order.symbol(), price);
			acceptedCounter.increment();
			return chain.next(order);
		});
	}
}
