"""The AI provider contract.

`suggest` returns `None` for every failure mode instead of raising: bad input,
an unexpected error, anything. That gives the orchestration layer exactly one
branch to handle, and means a malformed result can never be half-persisted
(Requirement 9.9).
"""

from typing import Protocol

from pydantic import BaseModel, Field

from app.models.enums import Category, Priority


class TriageSuggestion(BaseModel):
    category: Category
    priority: Priority
    summary: str = Field(max_length=200)
    draft_reply: str


class AIProvider(Protocol):
    def suggest(self, title: str, description: str) -> TriageSuggestion | None: ...
