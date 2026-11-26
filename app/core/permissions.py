from uuid import UUID, uuid4

from fastapi import Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.team import Role, TeamMember
from app.models.user import User

PERMISSIONS: dict[Role, frozenset[str]] = {
    Role.OWNER: frozenset({
        "team:read", "team:delete", "member:manage",
        "task:read", "task:create", "task:update", "task:delete",
    }),
    Role.MEMBER: frozenset({"team:read", "task:read", "task:create", "task:update"
    }),
    Role.MEMBER: frozenset({"team:read", "task:read", "task:create", "task:update"
    }),
    Role.VIEWER: frozenset({"team: read", "task:read"})
}

def require_permission(permission: str):
    async def check(
        team_id: UUID,
        user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db),
    ) -> TeamMember:
        member = await db.get(TeamMember, team_id, user.id)
        if member is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Team not found")
        if permission not in PERMISSIONS[member.role]:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Not enough permission")
        return member
    return checker