import json
import logging
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler

logger = logging.getLogger(__name__)

WEBHOOK_PORT = 8001


class _WebhookHandler(BaseHTTPRequestHandler):
    """Minimal HTTP handler that accepts POST /alerts from Grafana."""

    _grafana_handler = None

    def do_POST(self):
        if self.path != "/alerts":
            self.send_response(404)
            self.end_headers()
            return

        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length)

        try:
            payload = json.loads(body)
        except json.JSONDecodeError:
            logger.warning("Invalid JSON in webhook POST")
            self.send_response(400)
            self.end_headers()
            return

        try:
            self._grafana_handler.handle(payload)
            self.send_response(200)
            self.end_headers()
        except Exception:
            logger.exception("Error processing Grafana webhook")
            self.send_response(500)
            self.end_headers()

    def log_message(self, fmt, *args):
        logger.debug("Webhook: %s", fmt % args)


def start_webhook_server(grafana_handler):
    """Start the webhook HTTP server on a daemon thread."""
    _WebhookHandler._grafana_handler = grafana_handler
    server = HTTPServer(("0.0.0.0", WEBHOOK_PORT), _WebhookHandler)
    thread = threading.Thread(target=server.serve_forever, name="webhook_server", daemon=True)
    thread.start()
    logger.info("Webhook server started on :%d", WEBHOOK_PORT)
