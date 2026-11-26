from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.core.exceptions import (
    AlreadyMember,
    LastOwner,
    MemberNotFound,
    UserNotFound,
)
from app.core.permissions import require_permission
from app.models.team import Team, TeamMember
from app.models.user import User
from app.schemas.team import (
    MemberAdd,
    MemberRead,
    MemberRoleUpdate,
    TeamCreate,
    TeamRead,
    TeamSummary,
)
from app.services import team_service

router = APIRouter(prefix="/teams", tags=["teams"])

