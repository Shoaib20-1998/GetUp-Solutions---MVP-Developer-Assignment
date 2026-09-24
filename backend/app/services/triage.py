"""AI triage orchestration.

Called after the ticket row is already committed, so no AI outcome can affect
whether ticket creation succeeds (Requirement 9.7). The provider's result, if
any, is written only into the `ai_*` suggestion columns -- never into the
real `category` or `priority` fields. Only the confirmation endpoint
(task 11) does that.
"""

from sqlalchemy.orm import Session

from app.ai.base import AIProvider
from app.ai.mock_provider import MockAIProvider
from app.models import Ticket

_provider: AIProvider = MockAIProvider()


def set_provider(provider: AIProvider) -> None:
    """Swap the active provider. Used by tests to simulate failure
    (Requirement 15.2's "creation succeeding when the AI provider is
    unavailable") without touching module internals directly."""
    global _provider
    _provider = provider


def apply_triage(db: Session, ticket: Ticket) -> Ticket:
    """Run triage for `ticket` and persist suggestions, if any, in place."""
    try:
        suggestion = _provider.suggest(ticket.title, ticket.description)
    except Exception:
        # Any unexpected provider failure is treated the same as "no
        # suggestion": the ticket already exists and stays exactly as it is.
        suggestion = None

    if suggestion is not None:
        ticket.ai_suggested_category = suggestion.category
        ticket.ai_suggested_priority = suggestion.priority
        ticket.ai_summary = suggestion.summary
        ticket.ai_draft_reply = suggestion.draft_reply
        db.add(ticket)
        db.commit()
        db.refresh(ticket)

    return ticket
