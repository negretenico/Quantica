package com.negretenico.quantica.marketListener.stream;

public interface Publisher<T> {
	void publish(T message);
}
