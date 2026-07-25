import os
from dataclasses import dataclass
from dotenv import load_dotenv
load_dotenv()

@dataclass
class Config:
    DEBUG = os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'
    RABBITMQ_URL = os.environ.get('RABBITMQ_URL', 'amqp://guest:guest@localhost/')
    RABBITMQ_QUEUE = os.environ.get('RABBITMQ_QUEUE', 'signal.bard')
    ANALYTICS_EXCHANGE = os.environ.get('ANALYTICS_EXCHANGE', 'analytics')
    OPEN_AI_TOKEN = os.environ.get('OPEN_AI_TOKEN', 'sometokenhg')
    GH_TOKEN = os.environ.get('GH_TOKEN', 'sometokengh')
    GITHUB_REPO = os.environ.get('GITHUB_REPO', 'repo')
    GITHUB_BRANCH = os.environ.get('GITHUB_BRANCH', 'bard-updates')
    WINDOW_MINUTES = int(os.environ.get('WINDOW_MINUTES', '10'))
    MAX_SUMMARY_BUFFER = int(os.environ.get('MAX_SUMMARY_BUFFER', '50'))
    WINDOW_SUMMARY_MAX_TOKENS = int(os.environ.get('WINDOW_SUMMARY_MAX_TOKENS', '150'))
    SYNTHESIS_MAX_TOKENS = int(os.environ.get('SYNTHESIS_MAX_TOKENS', '800'))
    PUBLISHER_BACKEND = os.environ.get('PUBLISHER_BACKEND', 'github')
    BLOB_LOCAL_DIR    = os.environ.get('BLOB_LOCAL_DIR', '/tmp/marketbard')
    S3_BUCKET         = os.environ.get('S3_BUCKET', '')
    S3_PREFIX         = os.environ.get('S3_PREFIX', 'news')
    S3_REGION         = os.environ.get('S3_REGION', 'us-east-1')

    def __str__(self):
        return (f"RabbitMQ: {self.RABBITMQ_URL}\n"
                f"Queue: {self.RABBITMQ_QUEUE}")
