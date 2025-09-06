package consume

import (
	"context"
	"encoding/json"
	"log"
	"marketappendonly/model"
	"os"
	"os/signal"

	"github.com/IBM/sarama"
)

type Consumer struct {
	consumer sarama.ConsumerGroup
}

func NewConsumer() (*Consumer, error) {
	config := sarama.NewConfig()
	config.Consumer.Group.Rebalance.Strategy = sarama.BalanceStrategyRoundRobin
	config.Consumer.Offsets.Initial = sarama.OffsetOldest
	config.Consumer.Return.Errors = true

	consumer, err := sarama.NewConsumerGroup([]string{"localhost:9092"}, "ledger", config)
	if err != nil {
		return nil, err
	}

	return &Consumer{consumer: consumer}, nil
}

func (c *Consumer) StartConsumer(messageChan chan<- model.BinanceStreamResponse) {
	handler := &ConsumerGroupHandler{messageChan: messageChan}

	// create a cancellable context
	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()

	// listen for OS interrupts to stop cleanly
	go func() {
		sigchan := make(chan os.Signal, 1)
		signal.Notify(sigchan, os.Interrupt)
		<-sigchan
		cancel()
	}()

	for {
		// use the context, not nil
		if err := c.consumer.Consume(ctx, []string{"order"}, handler); err != nil {
			log.Printf("Error consuming: %v", err)
		}

		if ctx.Err() != nil {
			return
		}
	}
}

func (c *Consumer) Close() error {
	return c.consumer.Close()
}

// Handler implements sarama.ConsumerGroupHandler
type ConsumerGroupHandler struct {
	messageChan chan<- model.BinanceStreamResponse
}

func (h *ConsumerGroupHandler) Setup(sarama.ConsumerGroupSession) error   { return nil }
func (h *ConsumerGroupHandler) Cleanup(sarama.ConsumerGroupSession) error { return nil }

func (h *ConsumerGroupHandler) ConsumeClaim(session sarama.ConsumerGroupSession, claim sarama.ConsumerGroupClaim) error {
	for message := range claim.Messages() {
		var bsr model.BinanceStreamResponse
		if err := json.Unmarshal(message.Value, &bsr); err != nil {
			log.Printf("Error unmarshaling: %v", err)
			continue
		}
		h.messageChan <- bsr
		session.MarkMessage(message, "")
	}
	return nil
}
