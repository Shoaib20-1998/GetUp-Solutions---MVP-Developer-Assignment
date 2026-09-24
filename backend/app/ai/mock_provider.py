"""Deterministic, zero-cost stand-in for a real AI triage call.

No network call, no API key, no external dependency. Keyword rules pick a
category and priority, and a one-line summary and draft reply are templated
from the ticket title. Same input always yields the same output, which is
what "deterministic" means for Requirement 9.8: the app is fully demonstrable
without a paid key.
"""

import re

from app.ai.base import TriageSuggestion
from app.models.enums import Category, Priority

_CATEGORY_KEYWORDS: dict[Category, tuple[str, ...]] = {
    Category.BILLING: ("invoice", "charge", "payment", "refund", "billing", "subscription"),
    Category.TECHNICAL: ("error", "bug", "crash", "not working", "broken", "fail", "exception"),
    Category.ACCOUNT: ("password", "login", "account", "locked", "access", "email address"),
}

_URGENT_KEYWORDS = ("urgent", "asap", "immediately", "critical", "down", "outage")
_HIGH_KEYWORDS = ("important", "blocking", "cannot", "can't", "broken")
_LOW_KEYWORDS = ("minor", "cosmetic", "whenever", "small")


def _classify(text: str, keywords: dict[Category, tuple[str, ...]]) -> Category:
    for category, terms in keywords.items():
        if any(term in text for term in terms):
            return category
    return Category.GENERAL


def _prioritize(text: str) -> Priority:
    if any(term in text for term in _URGENT_KEYWORDS):
        return Priority.URGENT
    if any(term in text for term in _HIGH_KEYWORDS):
        return Priority.HIGH
    if any(term in text for term in _LOW_KEYWORDS):
        return Priority.LOW
    return Priority.MEDIUM


def _summarize(title: str) -> str:
    collapsed = re.sub(r"\s+", " ", title).strip()
    return collapsed[:197] + "..." if len(collapsed) > 200 else collapsed


class MockAIProvider:
    """The only provider. See `app/ai/base.py` for the contract it fulfils."""

    def suggest(self, title: str, description: str) -> TriageSuggestion | None:
        if not title.strip() and not description.strip():
            return None

        text = f"{title} {description}".lower()
        category = _classify(text, _CATEGORY_KEYWORDS)
        priority = _prioritize(text)
        summary = _summarize(title) or "New ticket"

        return TriageSuggestion(
            category=category,
            priority=priority,
            summary=summary,
            draft_reply=(
                f"Hi, thanks for reaching out about \"{title.strip()}\". "
                "We're looking into this and will follow up shortly."
            ),
        )
