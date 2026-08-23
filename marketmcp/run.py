import logging
import threading

from app.config import Config
from app.metrics import start_metrics_server
from app.stream import SignalStream, set_stream_instance
from mcp_server.server import mcp
import mcp_server.tools  # noqa: F401 — registers tool decorators
import mcp_server.resources  # noqa: F401 — registers resource decorators

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

    # Start real-time stream if enabled
    if config.STREAM_ENABLED:
        stream = SignalStream(config)
        set_stream_instance(stream)
        stream.start()
        logger.info("Real-time signal stream enabled")

    # Select transport
    transport = config.MCP_TRANSPORT
    if transport == "sse":
        logger.info("Running MCP server with SSE transport on %s:%d",
                    config.MCP_SSE_HOST, config.MCP_SSE_PORT)
        mcp.run(transport="sse", host=config.MCP_SSE_HOST, port=config.MCP_SSE_PORT)
    else:
        logger.info("Running MCP server with stdio transport")
        mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
