import os
from dataclasses import dataclass
from dotenv import load_dotenv
load_dotenv()

@dataclass
class Config:
    DEBUG = os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'
    KAFKA_BOOTSTRAP_SERVERS = os.environ.get('KAFKA_BOOTSTRAP_SERVERS', 'localhost:9092')
    KAFKA_CONSUMER_GROUP = os.environ.get('KAFKA_CONSUMER_GROUP', 'flask-consumer`-group')
    KAFKA_AUTO_OFFSET_RESET = os.environ.get('KAFKA_AUTO_OFFSET_RESET', 'latest')
    KAFKA_INPUT_TOPIC = os.environ.get('KAFKA_INPUT_TOPIC', 'input-topic')
    KAFKA_OUTPUT_TOPIC = os.environ.get('KAFKA_OUTPUT_TOPIC', 'output-topic')
    REDIS_HOST = os.environ.get('REDIS_HOST', 'localhost')
    OPEN_AI_TOKEN = os.environ.get('OPEN_AI_TOKEN', 'sometokenhg')
    GH_TOKEN = os.environ.get('GH_TOKEN', 'sometokengh')
    GITHUB_REPO = os.environ.get('GITHUB_REPO', 'repo')
    def __str__(self):
        return (f"Servers:{self.KAFKA_BOOTSTRAP_SERVERS}\n"
                f"Topics In: {self.KAFKA_INPUT_TOPIC}\n"
                f"Topics Out: {self.KAFKA_OUTPUT_TOPIC}")
