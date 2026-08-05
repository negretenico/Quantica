package com.negretenico.quantica.markettransformer.validation;

import com.negretenico.quantica.markettransformer.validation.price.PriceSanityGate;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

@Configuration
public class ValidationChainConfig {

	@Bean
	ValidationChain validationChain(PriceSanityGate priceSanityGate) {
		return ValidationChain.start()
				.then(priceSanityGate)
				.build();
	}
}
