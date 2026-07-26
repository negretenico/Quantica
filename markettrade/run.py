import logging
import threading

from app.config import Config
from app.rabbit_client import SignalRabbitClient

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    config = Config()
    client = SignalRabbitClient(config)

    def handle_message(payload):
        logger.debug(
            "Received signal — symbol=%s type=%s",
            payload.get("symbol"),
            payload.get("type"),
        )

    client.subscribe(handle_message)
    client.start_consuming()
    threading.Event().wait()


if __name__ == "__main__":
    main()
