package com.negretenico.quantica.markettransformer.validation.price;

import org.kie.api.KieBase;
import org.kie.api.io.ResourceType;
import org.kie.internal.utils.KieHelper;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.core.io.ClassPathResource;

import java.io.IOException;
import java.nio.charset.StandardCharsets;

@Configuration
public class DroolsConfig {

	@Bean
	KieBase priceSanityKieBase() throws IOException {
		KieHelper kieHelper = new KieHelper();
		String drl = new ClassPathResource("rules/price-sanity.drl")
				.getContentAsString(StandardCharsets.UTF_8);
		kieHelper.addContent(drl, ResourceType.DRL);
		return kieHelper.build();
	}
}
