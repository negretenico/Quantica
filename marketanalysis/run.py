import logging

from app import create_app, kafka_manager
from app.config import Config
from model.mini_batch import mini_batch
from analysis.outbound import send_msg

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

app = create_app()
kafka_manager.subscribe(topic=Config.KAFKA_INPUT_TOPIC, handler=lambda x,y: send_msg(prediction=mini_batch(x)))
if __name__ == '__main__':
    kafka_manager.start_consuming()

    try:
        app.run(host='0.0.0.0', port=5000, debug=app.config['DEBUG'])
    finally:
        kafka_manager.stop_consuming()
