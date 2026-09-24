"""AI triage orchestration.

Called after the ticket row is already committed, so no AI outcome can affect
whether ticket creation succeeds (Requirement 9.7). The provider's result, if
any, is written only into the `ai_*` suggestion columns -- never into the
real `category` or `priority` fields. Only the confirmation endpoint
(task 11) does that.
"""

from sqlalchemy.orm import Session

from app.ai.base import AIProvider
from app.ai.gemini_provider import GeminiAIProvider
from app.ai.mock_provider import MockAIProvider
from app.config import get_settings
from app.models import Ticket


def _select_provider() -> AIProvider:
    """Selected once at import time based on whether AI_API_KEY is set
    (Requirement 9.8). Gemini's own failure modes (network, timeout, bad
    schema) are handled inside GeminiAIProvider, which returns None just
    like the mock does on its "no input" case. If Gemini fails on a given
    request, `_get_suggestion` below retries once with the mock, so a
    suggestion is still shown whenever possible."""
    settings = get_settings()
    if settings.ai_api_key:
        return GeminiAIProvider(api_key=settings.ai_api_key, model=settings.ai_model)
    return MockAIProvider()


_provider: AIProvider = _select_provider()

# Always available as a second attempt when the primary provider is a real
# LLM and it fails. If the primary provider IS the mock (no API key set),
# this is simply never reached, since _provider already succeeds or is the
# same mock.
_fallback_provider: AIProvider = MockAIProvider()


def set_provider(provider: AIProvider) -> None:
    """Swap the active provider. Used by tests to simulate failure
    (Requirement 15.2's "creation succeeding when the AI provider is
    unavailable") without touching module internals directly."""
    global _provider
    _provider = provider


def _get_suggestion(title: str, description: str):
    """Try the primary provider; on any failure (returns None or raises),
    retry once with the deterministic mock so a suggestion is still shown
    whenever possible, real or mock. Ticket creation is never affected
    either way (Requirement 9.7)."""
    try:
        suggestion = _provider.suggest(title, description)
    except Exception:
        suggestion = None

    if suggestion is not None:
        return suggestion

    if isinstance(_provider, MockAIProvider):
        return None  # already the mock; nothing left to fall back to

    try:
        return _fallback_provider.suggest(title, description)
    except Exception:
        return None


def apply_triage(db: Session, ticket: Ticket) -> Ticket:
    """Run triage for `ticket` and persist suggestions, if any, in place."""
    suggestion = _get_suggestion(ticket.title, ticket.description)

    if suggestion is not None:
        ticket.ai_suggested_category = suggestion.category
        ticket.ai_suggested_priority = suggestion.priority
        ticket.ai_summary = suggestion.summary
        ticket.ai_draft_reply = suggestion.draft_reply
        db.add(ticket)
        db.commit()
        db.refresh(ticket)

    return ticket
