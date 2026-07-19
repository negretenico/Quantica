package com.negretenico.quantica.markettransformer.config;

import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.web.reactive.function.client.WebClient;

@Configuration
class RabbitManagementWebClientConfig {

	@Bean
	WebClient rabbitManagementWebClient(RabbitManagementProperties props, WebClient.Builder builder) {
		return builder.baseUrl(props.url()).build();
	}
}
