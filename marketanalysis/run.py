import logging
import threading
from collections import OrderedDict

from app import create_app, rabbit_manager
from app.config import Config
from model.mini_batch import mini_batch
from analysis.outbound import send_msg

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = create_app()

# Dedup seen-set: key = "symbol|eventTime|type", bounded at DEDUP_SET_SIZE (rolling eviction)
_seen: OrderedDict = OrderedDict()


def _handle_event(event):
    symbol = event.get("symbol", "")
    event_time = event.get("eventTime", "")
    event_type = event.get("type", "")
    dedup_key = f"{symbol}|{event_time}|{event_type}"

    if dedup_key in _seen:
        logger.debug(f"Duplicate event dropped: {dedup_key}")
        return

    _seen[dedup_key] = True
    if len(_seen) > Config.DEDUP_SET_SIZE:
        _seen.popitem(last=False)

    send_msg(prediction=mini_batch(event))


rabbit_manager.subscribe(handler=_handle_event)

if __name__ == '__main__':
    threading.Thread(target=rabbit_manager.start_consuming, daemon=True).start()
    app.run(host='0.0.0.0', port=5000, debug=Config.DEBUG)
