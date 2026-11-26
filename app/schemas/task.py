from uuid import UUID, uuid4
from datetime import datetime, date

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.task import Priority, TaskStatus

class TaskCreate(BaseModel):
    title: str = Field(min_length=1, max_digits=200)
    description: str | None = Field(default=None, max_length=2000)
    priority: Priority = Priority.MEDIUM
    due_date: date | None=None
    assignee_id: UUID | None=None

class TaskUpdate(BaseModel):
    title: str | None=Field(default=None, min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=2000)
    status: TaskStatus | None=None
    priority: Priority | None=None
    due_date: datetime | None=None
    assignee_id: UUID | None=None

    @field_validator("title", "status", "priority")
    @classmethod
    def not_null(cls, v):
        if v is None:
            raise ValueError("cannot be null")
        return v

class TaskRead(BaseModel):
    id: UUID
    team_id: UUID
    title: str
    description: str | None
    status: TaskStatus
    priority: Priority
    due_date: date | None
    assignee_id: UUID | None
    created_by: UUID | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

class TaskPage(BaseModel):
    items: list[TaskRead]
    total: int
    limit: int
    offset: int
    