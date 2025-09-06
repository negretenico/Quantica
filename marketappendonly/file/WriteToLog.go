package file

import (
	"encoding/json"
	"log"
	"marketappendonly/model" // Forward slash, matches your go.mod name
	"os"
	"time"
)

type Log struct {
	Timestamp int64  `json:"timestamp"`
	BuySell   bool   `json:"buy_sell"`
	EventType string `json:"event_type"`
	Data      []byte `json:"data"`
}

func WriteToLog(bsr model.BinanceStreamResponse) {
	log.Println("Begining Append")
	data, err := json.Marshal(bsr)
	if err != nil {
		panic(err)
	}
	f, err := os.OpenFile("history.log", os.O_CREATE|os.O_APPEND|os.O_WRONLY, 0600)
	if err != nil {
		panic(err)
	}
	defer f.Close() // Move defer right after opening file

	logg := Log{
		Timestamp: time.Now().Unix(),
		BuySell:   !bsr.IsBuyerMarketMaker, // false = buy, true = sell
		EventType: bsr.EventType,
		Data:      data,
	}
	logData, err := json.Marshal(logg)
	if err != nil {
		panic(err)
	}
	log.Println("Logging data " + string(logData))
	f.Write(logData)
	f.WriteString("\n")
}
