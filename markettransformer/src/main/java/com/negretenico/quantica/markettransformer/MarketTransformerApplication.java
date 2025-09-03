package com.negretenico.quantica.markettransformer;

import com.negretenico.quantica.markettransformer.model.KafkaProperties;
import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.boot.context.properties.EnableConfigurationProperties;

@SpringBootApplication
@EnableConfigurationProperties(KafkaProperties.class)
public class MarketTransformerApplication {

	public static void main(String[] args) {
		SpringApplication.run(MarketTransformerApplication.class, args);
	}

}
