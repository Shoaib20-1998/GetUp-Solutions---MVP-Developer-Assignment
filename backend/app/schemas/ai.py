from enum import StrEnum

from pydantic import BaseModel


class SuggestionField(StrEnum):
    CATEGORY = "category"
    PRIORITY = "priority"


class ApplySuggestionRequest(BaseModel):
    field: SuggestionField
