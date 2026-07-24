package com.negretenico.quantica.marketListener.model.events;

import org.springframework.context.ApplicationEvent;

public class WssDisconnected extends ApplicationEvent {
	public WssDisconnected(Object source) {
		super(source);
	}
}
