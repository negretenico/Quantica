# Quantica

make sure to run kafka, it can be started by doing 
```bash
docker run -p 9092:9092 apache/kafka-native:4.0.0
```

market listener needs to be started first to see events streaming
```bash
cd .\marketListener
mvn clean install -Dspring-boot.run.profiles=local
```