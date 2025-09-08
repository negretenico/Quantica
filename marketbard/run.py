import threading
import time
import logging

from app.config import Config
from gh.github_client import GithubClient
from apache_kafka.kafka_client import KafkaClientManager
from redis_cache.redis_client import RedisClient
from model.hugging_face_client import HuggingFace
from model.build_prompt import build_prompt

logger = logging.getLogger(__name__)

redis_client = RedisClient(host=Config.REDIS_HOST)
hugging_face_client = HuggingFace(Config.HF_TOKEN)
github_client = GithubClient(Config.GITHUB_TOKEN, Config.GITHUB_REPO)


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
    """Thread that consumes from gen_queue → calls HuggingFace → pushes to write_queue"""
    while True:
        batch = redis_client.get_latest_gen_queue()
        if not batch:
            time.sleep(2)
            continue

        events = batch["events"]
        prompt = build_prompt(events)
        story = hugging_face_client.create_story(prompt, len(events))
        redis_client.add_story(story)




def writer():
    """Thread that consumes from write_queue → commits to GitHub"""
    while True:
        story = redis_client.get_latest_story()
        if not story:
            time.sleep(2)
            continue

        github_client.write_story(story["story_md"])
        logger.info("Committed new story to GitHub")


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
