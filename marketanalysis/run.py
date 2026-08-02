import logging
import threading

from app import create_app, rabbit_manager
from app.config import Config
from model.mini_batch import mini_batch
from analysis.outbound import send_msg
from shared.dedup import DedupFilter

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = create_app()

_dedup = DedupFilter(maxlen=Config.DEDUP_SET_SIZE)


def _handle_event(event):
    if _dedup.is_duplicate(event):
        logger.debug("Duplicate event dropped: %s", event.get("symbol"))
        return

    send_msg(prediction=mini_batch(event))


rabbit_manager.subscribe(handler=_handle_event)

if __name__ == '__main__':
    threading.Thread(target=rabbit_manager.start_consuming, daemon=True).start()
    app.run(host='0.0.0.0', port=5000, debug=Config.DEBUG)
