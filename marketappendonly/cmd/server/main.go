package main

import (
	"log"
	"marketappendonly/consume"
	"marketappendonly/file"
	"marketappendonly/model"
)

func main() {
	log.Println("Starting Append only")
	consumer, err := consume.NewConsumer()
	if err != nil {
		log.Fatal("Failed to create consumer:", err)
	}
	defer consumer.Close()
	messageChan := make(chan model.BinanceStreamResponse, 100)

	// Start consumer
	go consumer.StartConsumer(messageChan)

	log.Println("Starting consumer...")

	// Process messages
	for message := range messageChan {
		log.Println("Consuming message " + message.EventType)
		file.WriteToLog(message)
	}
}
