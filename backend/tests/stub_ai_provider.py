"""A provider stub whose behaviour tests can switch between success and
failure, standing in for the real AI provider (Requirement 15.5: the AI
provider may be stubbed since it's an external paid dependency)."""

from app.ai.base import TriageSuggestion
from app.models.enums import Category, Priority


class FailingAIProvider:
    """Always raises, simulating a provider outage or timeout."""

    def suggest(self, title: str, description: str) -> TriageSuggestion | None:
        raise RuntimeError("simulated AI provider failure")


class SucceedingAIProvider:
    """Always returns a fixed, valid suggestion."""

    def suggest(self, title: str, description: str) -> TriageSuggestion | None:
        return TriageSuggestion(
            category=Category.TECHNICAL,
            priority=Priority.HIGH,
            summary="Stubbed summary",
            draft_reply="Stubbed draft reply.",
        )
