import redis
import json
import time
import logging
logger = logging.getLogger(__name__)
class RedisClient:

    def __init__(self, host,batch_size=50,max_wait=60):
        self.client = redis.Redis(host=host, port=6379, db=0)
        self._BUFFER_KEY = 'market:buffer:default'
        self._GEN_QUEUE_KEY = 'market:gen_queue'
        self._WRITE_QUEUE_KEY = 'market:write_queue'
        self._LOCK_KEY = 'market:lock:coordinator'
        self._LOCK_TTL = 30
        self._BATCH_SIZE = batch_size
        self._MAX_WAIT = max_wait
    
    async def add_to_gen_queue(self, events):
        logger.info(f"Adding the events {events} to the queue")
        await self.redis.rpush(self.GEN_QUEUE_KEY, json.dumps({"events": events, "created_at": time.time()}))

    def get_latest_gen_queue(self):
        return json.loads(self.redis.lpop(self._GEN_QUEUE_KEY))

    async def add_story(self, story):
        logger.info(f"Adding story {story} to the queue")
        await self.redis.rpush(self.WRITE_QUEUE_KEY, json.dumps(story))

    def get_latest_story(self):
        return json.loads(self.redis.lpop(self._WRITE_QUEUE_KEY))

    async def add_to_buffer(self, event):
        logger.info(f"Adding event {event} to the buffer")
        await self.redis.rpush(self.BUFFER_KEY, json.dumps(event))

    def get_latest_buffer_item(self):
        return json.loads(self.redis.lpop(self._BUFFER_KEY))

    async def try_become_leader(self):
        logger.info("trying to become the leader")
        return await self.redis.set(self._LOCK_KEY, "1", exist=redis.SET_IF_NOT_EXIST, expire=self._LOCK_TTL)

