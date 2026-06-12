import json
import os
import logging
import threading
from openai import OpenAI

logger = logging.getLogger(__name__)

_WINDOW_CATEGORIES = ["BULLISH", "BEARISH", "NEUTRAL", "HIGH_VOLATILITY"]

# Structured output schema — enforces {narrative_summary, category} on every window call
_WINDOW_SCHEMA = {
    "type": "json_schema",
    "json_schema": {
        "name": "window_summary",
        "strict": True,
        "schema": {
            "type": "object",
            "properties": {
                "narrative_summary": {"type": "string"},
                "category": {"type": "string", "enum": _WINDOW_CATEGORIES},
            },
            "required": ["narrative_summary", "category"],
            "additionalProperties": False,
        },
    },
}


class OpenAIClient:
    def __init__(self, api_key: str | None = None):
        self.client = OpenAI(api_key=api_key or os.getenv("OPENAI_API_KEY"))
        self.lock = threading.Lock()

    def create_story(self, prompt: str, count: int, max_new_tokens: int = 500, temperature: float = 0.7):
        with self.lock:
            logger.debug(f"Generating story for {count} events...")
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are a creative storyteller."},
                    {"role": "user", "content": prompt},
                ],
                max_tokens=max_new_tokens,
                temperature=temperature,
                timeout=60,
            )
        story_md = response.choices[0].message.content.strip()
        return {"story_md": story_md, "meta": {"events_count": count}}

    def create_window_summary(self, prompt: str, max_tokens: int = 150) -> dict:
        """
        Structured output call for a single 10-minute window.
        Returns a parsed dict: {narrative_summary: str, category: str}.
        max_tokens enforces conciseness so synthesis context stays bounded.
        """
        with self.lock:
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are a concise financial market analyst."},
                    {"role": "user", "content": prompt},
                ],
                max_tokens=max_tokens,
                temperature=0.3,
                response_format=_WINDOW_SCHEMA,
                timeout=30,
            )
        return json.loads(response.choices[0].message.content)

    def create_synthesis(self, prompt: str, max_tokens: int = 800, temperature: float = 0.7) -> str:
        """All-day narrative from accumulated window summaries."""
        with self.lock:
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are a creative financial market storyteller."},
                    {"role": "user", "content": prompt},
                ],
                max_tokens=max_tokens,
                temperature=temperature,
                timeout=60,
            )
        return response.choices[0].message.content.strip()
