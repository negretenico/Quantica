import logging

from app.config import Config

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    logger.info("Starting MarketTrade")
    logger.info(Config())
    logger.info("MarketTrade skeleton started successfully — no logic yet")


if __name__ == "__main__":
    main()
