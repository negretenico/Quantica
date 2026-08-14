"""Deterministic fake OpenAI client for e2e testing.

Returns canned responses with an ``[E2E_FAKE]`` marker so tests can
assert the blob content came from the mock rather than a real LLM call.
"""

import logging

logger = logging.getLogger(__name__)


class FakeOpenAIClient:

    def create_window_summary(self, prompt: str, max_tokens: int = 150) -> dict:
        logger.info("FakeOpenAIClient: returning canned window summary")
        return {
            "narrative_summary": "[E2E_FAKE] Stable trading session with moderate volume.",
            "category": "NEUTRAL",
        }

    def create_synthesis(self, prompt: str, max_tokens: int = 800, temperature: float = 0.7) -> str:
        logger.info("FakeOpenAIClient: returning canned synthesis")
        return "[E2E_FAKE] Daily synthesis: markets were calm with no significant anomalies detected."
