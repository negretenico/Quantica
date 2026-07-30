import logging

from app import create_app
from app.config import Config

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

app = create_app()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=Config.BLOB_SERVER_PORT, debug=Config.DEBUG)
