import logging

from app import create_app, rabbit_manager
from model.mini_batch import mini_batch
from analysis.outbound import send_msg

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

app = create_app()
rabbit_manager.subscribe(handler=lambda event: send_msg(prediction=mini_batch(event)))

if __name__ == '__main__':
    rabbit_manager.start_consuming()

    try:
        app.run(host='0.0.0.0', port=5000, debug=app.config['DEBUG'])
    finally:
        pass
