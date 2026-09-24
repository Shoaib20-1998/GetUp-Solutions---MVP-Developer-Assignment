"""Real LLM provider: Google Gemini, called over plain HTTPS via `httpx`
rather than the SDK, since the REST call is simple enough not to need it.

Contract (see `ai/base.py`): `suggest` returns `None` for network error,
timeout, non-2xx response, unparseable JSON, or output that fails
`TriageSuggestion` validation, so no partial or malformed suggestion can be
stored (Requirement 9.9) and ticket creation is never affected by an AI
failure (Requirement 9.7). This provider never raises.
"""

import json
import logging

import httpx
from pydantic import ValidationError

from app.ai.base import TriageSuggestion
from app.models.enums import Category, Priority

logger = logging.getLogger("app.ai.gemini")

_ENDPOINT_TEMPLATE = (
    "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
)
_TIMEOUT_SECONDS = 8.0

_PROMPT_TEMPLATE = """You are a support-ticket triage assistant. Given a ticket title \
and description, respond with ONLY a JSON object (no markdown, no code fences) with \
exactly these keys:
- "category": one of {categories}
- "priority": one of {priorities}
- "summary": a one-line summary, 200 characters or fewer
- "draft_reply": a short, friendly draft reply to the customer

Title: {title}
Description: {description}
"""


class GeminiAIProvider:
    def __init__(self, api_key: str, model: str) -> None:
        self._api_key = api_key
        self._model = model

    def suggest(self, title: str, description: str) -> TriageSuggestion | None:
        prompt = _PROMPT_TEMPLATE.format(
            categories=[c.value for c in Category],
            priorities=[p.value for p in Priority],
            title=title,
            description=description,
        )

        try:
            response = httpx.post(
                _ENDPOINT_TEMPLATE.format(model=self._model),
                params={"key": self._api_key},
                json={
                    "contents": [{"parts": [{"text": prompt}]}],
                    "generationConfig": {"responseMimeType": "application/json"},
                },
                timeout=_TIMEOUT_SECONDS,
            )
            response.raise_for_status()
        except httpx.HTTPError as exc:
            logger.warning("Gemini request failed: %s", exc)
            return None

        try:
            payload = response.json()
            text = payload["candidates"][0]["content"]["parts"][0]["text"]
            parsed = json.loads(text)
            return TriageSuggestion.model_validate(parsed)
        except (KeyError, IndexError, json.JSONDecodeError, ValidationError) as exc:
            logger.warning("Gemini response did not match the expected schema: %s", exc)
            return None
