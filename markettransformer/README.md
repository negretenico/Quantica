```bash
mvn spring-boot:run -Dspring-boot.run.profiles=local
```



Large trade detected: If a trade’s quantity is above a certain threshold → emit LargeTradeEvent. 
Aggressive buyer/seller: If the same side dominates for N trades in a row → emit DominantSideEvent. 
Price spike/dip: If price moves more than X% in a short period → emit PriceSpikeEvent or PriceDipEvent. 
Volume per interval: Aggregate quantity per symbol every N seconds → VolumeMetricEvent. 
VWAP (Volume Weighted Average Price): Every N seconds → VWAPMetricEvent