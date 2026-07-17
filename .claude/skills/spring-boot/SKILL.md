---
name: spring-boot
description: Spring Boot conventions — constructor injection, ConfigurationProperties, ControllerAdvice, Kafka error handling, domain packaging, and config-based profiles. Use when adding Spring configuration, creating new beans, wiring Kafka consumers, or structuring Spring Boot modules.
---

# Spring Boot Conventions

These conventions apply to all Spring Boot code in this project. Read the `/java` skill first — these conventions extend it, not replace it.

## Records vs Spring Beans

Records are for **data**. Classes are for **Spring beans**.

Spring's CGLIB proxying (used by `@Transactional`, AOP, and others) requires subclassing — records are implicitly `final` and cannot be proxied. Any class annotated with `@Component`, `@Service`, `@Repository`, or `@Controller` must be a regular class.

Records survive everywhere Spring doesn't manage the lifecycle: DTOs, Kafka message payloads, domain value objects, `@ConfigurationProperties` bindings, API request/response bodies.

## Constructor Injection

Constructor injection is the only allowed injection style. Field injection (`@Autowired` on fields) is banned — it hides dependencies, requires reflection, and prevents testing without a Spring context.

```java
// banned
@Service
public class OddsService {
    @Autowired
    private OddsClient client;
}

// required
@Service
public class OddsService {
    private final OddsClient client;

    public OddsService(OddsClient client) {
        this.client = client;
    }
}
```

Spring 4.3+ auto-detects a single constructor — no `@Autowired` annotation needed.

**Dependency limit:** Target 2 dependencies per class. 3 is the hard limit. More than 3 is a mandatory refactor signal — the class is doing too much.

## Configuration

Use `@ConfigurationProperties` with records for all grouped configuration. `@Value` is a code smell — it scatters config assumptions across the codebase and provides no upfront validation.

```java
// banned
@Value("${odds.api.key}")
private String apiKey;

// required
@ConfigurationProperties(prefix = "odds.api")
record OddsApiConfig(String key, String baseUrl, int timeoutSeconds) {}
```

Register config records with `@EnableConfigurationProperties(OddsApiConfig.class)` in a `@Configuration` class. Add `spring-boot-configuration-processor` to get IDE autocompletion and validation.

## Exception Handling — REST

`@ControllerAdvice` is the single error boundary for REST. Controllers have zero try-catch blocks — they call services and return results. All exception-to-HTTP mapping lives in one `@ControllerAdvice` class.

Domain exceptions are **HTTP-unaware**. The exception describes what went wrong; the handler decides what status code the consumer receives.

```java
// banned — exception knows about HTTP
@ResponseStatus(HttpStatus.NOT_FOUND)
public class GameNotFoundException extends RuntimeException { ... }

// required — handler owns the mapping
@RestControllerAdvice
public class GlobalExceptionHandler {

    @ExceptionHandler(GameNotFoundException.class)
    public ResponseEntity<ErrorResponse> handle(GameNotFoundException e) {
        return ResponseEntity.status(404).body(new ErrorResponse(e.getMessage()));
    }

    @ExceptionHandler(OddsFetchException.class)
    public ResponseEntity<ErrorResponse> handle(OddsFetchException e) {
        return ResponseEntity.status(502).body(new ErrorResponse(e.getMessage()));
    }
}
```

One `@ExceptionHandler` method per exception type.

## Kafka Error Handling

Kafka listener methods are try-catch free. Error handling — retries, dead-letter routing, logging — is wired via `DefaultErrorHandler` in a `@Configuration` class. There is no per-topic error handling; one handler governs all consumers.

```java
// banned — error handling inside the listener
@KafkaListener(topics = "game-events")
public void consume(GameEvent event) {
    try {
        pipeline.process(event);
    } catch (GameEventParseException e) {
        deadLetterTemplate.send("game-events.DLT", event);
    }
}

// required — listener is pure processing logic
@KafkaListener(topics = "game-events")
public void consume(GameEvent event) {
    pipeline.process(event);
}

// error handling wired in @Configuration
@Bean
public DefaultErrorHandler errorHandler(KafkaTemplate<?, ?> template) {
    DeadLetterPublishingRecoverer recoverer = new DeadLetterPublishingRecoverer(template);
    return new DefaultErrorHandler(recoverer, new FixedBackOff(1000L, 3));
}
```

## Package Structure

Organize by **business domain**, not by layer. Each domain owns all of its Spring beans, records, exceptions, and config co-located in one package.

```
com.stochasticsports
  ├── odds/
  │   ├── OddsConsumer.java        # @KafkaListener
  │   ├── OddsService.java         # @Service
  │   ├── OddsClient.java          # HTTP client
  │   ├── OddsSnapshot.java        # record
  │   ├── OddsApiConfig.java       # @ConfigurationProperties record
  │   └── OddsFetchException.java  # unchecked exception
  ├── gameevents/
  │   ├── GameEventConsumer.java
  │   ├── GameEventService.java
  │   ├── GameEvent.java
  │   └── GameEventParseException.java
  └── shared/
      └── ErrorResponse.java       # only truly cross-cutting types here
```

Never create a top-level `services/`, `controllers/`, or `exceptions/` package. If code belongs to a domain, it lives in that domain's package.

## Profiles

Use profile-specific config files for environment differences. No `@Profile`-annotated beans.

```
src/main/resources/
  application.yml          # shared defaults
  application-dev.yml      # local overrides (dev API keys, local Kafka)
  application-prod.yml     # production values
```

If a bean needs to behave differently per environment, it should accept a config value rather than be swapped via `@Profile`. A bean that exists in dev but not prod is a production surprise waiting to happen.
