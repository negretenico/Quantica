import os
import logging
import threading
from openai import OpenAI

logger = logging.getLogger(__name__)

class OpenAIClient:
    def __init__(self, api_key: str | None = None):
        """
        Initialize the OpenAI client.
        Reads from environment variable OPENAI_API_KEY if api_key is not provided.
        """
        self.client = OpenAI(api_key=api_key or os.getenv("OPENAI_API_KEY"))
        self.lock = threading.Lock()

    def create_story(
        self,
        prompt: str,
        count: int,
        max_new_tokens: int = 500,
        temperature: float = 0.7
    ):
        """
        Generate a story using OpenAI's API.
        Matches the HuggingFace client interface.
        """
        with self.lock:
            logger.debug(f"Generating story for {count} events...")

            response = self.client.chat.completions.create(
                model="gpt-4o-mini",  # cheap + capable
                messages=[
                    {"role": "system", "content": "You are a creative storyteller."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=max_new_tokens,
                temperature=temperature,
            )

        story_md = response.choices[0].message.content.strip()
        return {"story_md": story_md, "meta": {"events_count": count}}

