FROM maven:3.9-eclipse-temurin-21 AS builder

ARG GITHUB_TOKEN

WORKDIR /build

RUN mkdir -p /root/.m2 && \
    printf '<settings><servers><server><id>github</id><username>negretenico</username><password>%s</password></server><server><id>github-functionico</id><username>negretenico</username><password>%s</password></server></servers></settings>' \
    "${GITHUB_TOKEN}" "${GITHUB_TOKEN}" > /root/.m2/settings.xml

COPY pom.xml .
RUN mvn dependency:go-offline -B

COPY src ./src
RUN mvn package -DskipTests -B

FROM eclipse-temurin:21-jre

RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY --from=builder /build/target/*.jar app.jar

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=3s --start-period=60s --retries=3 \
  CMD curl -f http://localhost:8080/actuator/health || exit 1

ENTRYPOINT ["java", "-jar", "app.jar"]
