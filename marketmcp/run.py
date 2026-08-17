import logging
import threading

from mcp.server import MCPServer

from app.config import Config
from app.metrics import start_metrics_server

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

mcp = MCPServer("marketmcp")


def main():
    config = Config()
    logging.getLogger().setLevel(config.LOG_LEVEL)
    logger.info("Starting marketmcp\n%s", config)

    metrics_thread = threading.Thread(
        target=start_metrics_server,
        args=(config.METRICS_PORT,),
        daemon=True,
    )
    metrics_thread.start()
    logger.info("Prometheus metrics server started on :%d", config.METRICS_PORT)

    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
