package com.negretenico.quantica.markettransformer.validation;

import com.negretenico.quantica.markettransformer.model.BinanceStreamResponse;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

import static org.junit.jupiter.api.Assertions.*;

@ExtendWith(MockitoExtension.class)
class ValidationChainTest {

	@Mock
	BinanceStreamResponse order;

	@Test
	void emptyChainAccepts() {
		ValidationChain chain = ValidationChain.start().build();
		OrderValidationResult result = chain.execute(order);
		assertTrue(result.accepted());
		assertNull(result.reason());
	}

	@Test
	void singleValidatorRejects() {
		ValidationChain chain = ValidationChain.start()
				.then((o, c) -> OrderValidationResult.reject("bad price"))
				.build();

		OrderValidationResult result = chain.execute(order);
		assertFalse(result.accepted());
		assertEquals("bad price", result.reason());
	}

	@Test
	void singleValidatorAccepts() {
		ValidationChain chain = ValidationChain.start()
				.then((o, c) -> c.next(o))
				.build();

		OrderValidationResult result = chain.execute(order);
		assertTrue(result.accepted());
	}

	@Test
	void chainStopsOnFirstRejection() {
		boolean[] secondCalled = {false};

		ValidationChain chain = ValidationChain.start()
				.then((o, c) -> OrderValidationResult.reject("first rejects"))
				.then((o, c) -> {
					secondCalled[0] = true;
					return c.next(o);
				})
				.build();

		OrderValidationResult result = chain.execute(order);
		assertFalse(result.accepted());
		assertEquals("first rejects", result.reason());
		assertFalse(secondCalled[0]);
	}

	@Test
	void chainPassesThroughAllValidators() {
		boolean[] firstCalled = {false};
		boolean[] secondCalled = {false};

		ValidationChain chain = ValidationChain.start()
				.then((o, c) -> {
					firstCalled[0] = true;
					return c.next(o);
				})
				.then((o, c) -> {
					secondCalled[0] = true;
					return c.next(o);
				})
				.build();

		OrderValidationResult result = chain.execute(order);
		assertTrue(result.accepted());
		assertTrue(firstCalled[0]);
		assertTrue(secondCalled[0]);
	}

	@Test
	void chainIsReentrant() {
		ValidationChain chain = ValidationChain.start()
				.then((o, c) -> c.next(o))
				.build();

		OrderValidationResult first = chain.execute(order);
		OrderValidationResult second = chain.execute(order);
		assertTrue(first.accepted());
		assertTrue(second.accepted());
	}
}
