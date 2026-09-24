from pydantic import BaseModel

from app.models.enums import Priority, Status


class DashboardResponse(BaseModel):
    counts_by_status: dict[Status, int]
    counts_by_priority: dict[Priority, int]
    average_resolution_hours: float | None
    stale_open_count: int
