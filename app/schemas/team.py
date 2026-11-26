from uuid import UUID, uuid4
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field
from app.models.team import Role

class TeamCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)

class TeamRead(BaseModel):
    id: UUID
    name: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

class TeamSummary(TeamRead):
    role: Role

class MemberAdd(BaseModel):
    email: EmailStr
    role: Role = Role.MEMBER

class MemberRoleUpdate(BaseModel):
    role: Role

class MemberRead(BaseModel):
    user_id: UUID
    email: EmailStr
    role: Role