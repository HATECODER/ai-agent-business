"""Validated input and response shapes used by the tool layer."""

from typing import Literal
from pydantic import BaseModel, Field


Priority = Literal["low", "medium", "high", "critical"]
TaskStatus = Literal["pending", "in_progress", "completed"]
TaskCategory = Literal["operations", "growth", "finance", "restock"]


class TaskInput(BaseModel):
    title: str = Field(min_length=3, max_length=160)
    description: str = Field(default="", max_length=1000)
    priority: Priority = "medium"
    category: TaskCategory = "operations"
    related_entity_type: str | None = None
    related_entity_id: int | None = Field(default=None, gt=0)


class CampaignInput(BaseModel):
    segment_description: str = Field(min_length=3, max_length=300)
    objective: str = Field(min_length=3, max_length=200)
    offer: str | None = Field(default=None, max_length=200)
    channel: Literal["sms", "email", "facebook", "whatsapp"] = "facebook"
