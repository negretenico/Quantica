import os
from dataclasses import dataclass


@dataclass
class Config:
    KAFKA_BOOTSTRAP: str = os.environ.get("KAFKA_BOOTSTRAP", "localhost:9092")
    KAFKA_TOPIC: str = os.environ.get("KAFKA_TOPIC", "order")
    KAFKA_TIMEOUT_SECONDS: int = int(os.environ.get("KAFKA_TIMEOUT_SECONDS", "30"))
