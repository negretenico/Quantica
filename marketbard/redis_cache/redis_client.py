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

    def flush_buffer_if_ready(self):
        buffer_len = self.client.llen(self._BUFFER_KEY)
        if buffer_len >= self._BATCH_SIZE:
            self._flush_buffer()
        else:
            # check oldest item age
            oldest_item = self.client.lindex(self._BUFFER_KEY, 0)
            if oldest_item:
                created_at = json.loads(oldest_item).get("created_at", time.time())
                if time.time() - created_at >= self._MAX_WAIT:
                    self._flush_buffer()

    def _flush_buffer(self):
        batch = []
        for _ in range(self._BATCH_SIZE):
            item = self.client.lpop(self._BUFFER_KEY)
            if not item:
                break
            batch.append(json.loads(item))
        if batch:
            self.add_to_gen_queue(batch)
