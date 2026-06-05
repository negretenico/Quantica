package com.negretenico.quantica.markettransformer.config;

import org.springframework.amqp.core.Binding;
import org.springframework.amqp.core.BindingBuilder;
import org.springframework.amqp.core.FanoutExchange;
import org.springframework.amqp.core.Queue;
import org.springframework.amqp.support.converter.Jackson2JsonMessageConverter;
import org.springframework.amqp.support.converter.MessageConverter;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

@Configuration
public class RabbitConfig {

	public static final String EXCHANGE = "signal";
	public static final String ANALYSIS_QUEUE = "signal.analysis";
	public static final String BARD_QUEUE = "signal.bard";

	@Bean
	public FanoutExchange signalExchange() {
		return new FanoutExchange(EXCHANGE);
	}

	@Bean
	public Queue analysisQueue() {
		return new Queue(ANALYSIS_QUEUE, true);
	}

	@Bean
	public Queue bardQueue() {
		return new Queue(BARD_QUEUE, true);
	}

	@Bean
	public Binding analysisBinding() {
		return BindingBuilder.bind(analysisQueue()).to(signalExchange());
	}

	@Bean
	public Binding bardBinding() {
		return BindingBuilder.bind(bardQueue()).to(signalExchange());
	}

	@Bean
	public MessageConverter jsonMessageConverter() {
		return new Jackson2JsonMessageConverter();
	}
}
