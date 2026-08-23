import logging
import threading

from app.config import Config
from app.metrics import start_metrics_server
from mcp_server.server import mcp
import mcp_server.tools  # noqa: F401 — registers tool decorators
import mcp_server.resources  # noqa: F401 — registers resource decorators
import mcp_server.prompts  # noqa: F401 — registers prompt decorators

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


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
