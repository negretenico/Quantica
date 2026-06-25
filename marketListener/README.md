# Market Listener

## Summary

This application's goal is to listen live market data through a websocket
seralize it and send it to a kafka topic.

---

## Running the application

Prerequisites

- A running Kafka cluster accessible at `localhost:9092`.
- A configured Kafka topic for raw market events.
- Java 21 and Maven installed, or use the included Maven wrapper.

Run locally

```bash
./mvnw spring-boot:run -Dspring-boot.run.profiles=local
```

On Windows PowerShell:

```powershell
./mvnw.cmd spring-boot:run -Dspring-boot.run.profiles=local
```

When the application is running properly, you should see the connection and publish logs in console output, similar to the screenshot below.

![CONNECTION_PUBLISH.JPG](images/CONNECTION_PUBLISH.JPG)

---

## Architecture

```
Market Data Source → WebSocket Client → Event Publisher → Kafka Producer → Kafka Topic
```

1. **WebSocket Listener:** Connects to market data providers (exchanges, data feeds)
2. **Event Publisher:** Uses Spring Events to decouple WebSocket handling from message processing
3. **Message Serializer:** Converts market data to standardized format (JSON/Avro)
4. **Kafka Producer:** Publishes serialized messages to configured Kafka topics

---

## Tech stack

- **Java 21** - Latest LTS version for optimal performance and modern language features
- **Spring Boot 3.x** - Application framework with auto-configuration and production-ready features
- **Spring Events** - Decoupled event-driven architecture for internal messaging
- **WebSockets** - Real-time bidirectional communication for market data streaming
- **Apache Kafka** - Distributed streaming platform for reliable message queuing
- **Maven 3.6.5+** - Dependency management and build automation
- **Jackson** - JSON serialization/deserialization
- **SLF4J + Logback** - Structured logging framework

---

## Troubleshooting

### Common Issues

- WebSocket Connection Fails
  - Verify market data source URL and authentication
  - Check network connectivity and firewall rules
  - Review WebSocket client logs for detailed errors

- Kafka Publishing Errors
  - Ensure Kafka cluster is running and accessible
  - Verify topic exists and has correct permissions
  - Check serialization configuration

- High Memory Usage
  - Tune JVM heap settings: -Xmx2g -Xms1g
  - Review message buffering configuration
  - Monitor for memory leaks in WebSocket handlers
