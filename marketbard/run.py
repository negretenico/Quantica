import threading
import time
import logging

from app.config import Config
from gh.github_client import GithubClient
from apache_kafka.kafka_client import KafkaClientManager
from redis_cache.redis_client import RedisClient
from model.openai_client import OpenAIClient
from model.build_prompt import build_prompt
# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

redis_client = RedisClient(host=Config.REDIS_HOST, batch_size=3, max_wait=5)
openai_client = OpenAIClient(Config.OPEN_AI_TOKEN)
github_client = GithubClient(token=Config.GH_TOKEN,repo_name= Config.GITHUB_REPO)


def kafka_event_handler(event, key):
    """Handler called by Kafka consumer for each new event"""
    logger.info(f"Received event from Kafka: {event}")
    redis_client.add_to_buffer(event)


def buffer_flusher():
    """Thread that moves batches from buffer → gen_queue"""
    while True:
        redis_client.flush_buffer_if_ready()
        time.sleep(2)

def story_worker():
    while True:
        logger.info("story_worker: checking gen_queue…")
        batch = redis_client.get_latest_gen_queue()
        if not batch:
            logger.debug("story_worker: no batch found")
            time.sleep(2)
            continue

        logger.info(f"story_worker: got batch with {len(batch['events'])} events")
        events = batch["events"]
        prompt = build_prompt(events)
        story =  openai_client.create_story(prompt, len(events))
        redis_client.add_story(story)
        logger.info("story_worker: added story to write_queue")


def writer():
    while True:
        logger.info("writer: checking write_queue…")
        story = redis_client.get_latest_story()
        if not story:
            logger.debug("writer: no story found")
            time.sleep(2)
            continue

        story_md = story["story_md"].replace("\\n", "\n")
        github_client.write_story(story_md)
        logger.info("writer: committed new story to GitHub")



def main():
    logger.info("Starting MarketBard")
    kafka_manager = KafkaClientManager(config=Config)
    kafka_manager.subscribe(
        topic=Config.KAFKA_INPUT_TOPIC,
        handler=kafka_event_handler
    )
    threading.Thread(target=buffer_flusher, daemon=True).start()
    threading.Thread(target=story_worker, daemon=True).start()
    threading.Thread(target=writer, daemon=True).start()

    kafka_manager.start_consuming()

    # Block forever to keep the main thread alive
    try:
        while True:
            time.sleep(60)
    except KeyboardInterrupt:
        logger.info("Shutting down cleanly…")


if __name__=="__main__":
    main()