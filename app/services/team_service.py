from uuid import UUID

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import (
    AlreadyMember, 
    LastOwner,
    MemberNotFound,
    UserNotFound,
)
from app.models.team import Role, Team, TeamMember
from app.models.user import User
from app.services.user_service import get_user_by_email


async def create_team(db: AsyncSession, user: User, name: str) -> Team:
    team = Team(name=name)
    db.add(team)
    await db.flush()
    db.add(TeamMember(team_id=team.id, user_id=user.id, role=Role.OWNER))
    await db.commit()
    await db.refresh(team)
    return team

async def list_teams_for_user(db: AsyncSession, user_id: UUID) -> list[dict]:
    stmt = (
        select(Team, TeamMember.role)
        .join(TeamMember, TeamMember.team_id == Team.id)
        .where(TeamMember.user_id == user_id)
        .order_by(Team.created_at)
    )

    rows = (await db.execute(stmt)).all()
    return [
        {"id": t.id, "name": t.name, "created_at": t.created_at, "role": role}
        for t, role in rows
    ]

async def list_members(db: AsyncSession, team_id: UUID) -> list[TeamMember]:
    result = await db.execute(select(TeamMember).where(TeamMember.team_id == team_id))
    return list(result.scalars().all())


async def _owner_count(db: AsyncSession, team_id: UUID) -> int:
    result = await db.execute(
        select(func.count())
        .select_from(TeamMember)
        .where(TeamMember.team_id == team_id, TeamMember.role == Role.OWNER)
    )
    return result.scalar_one()

async def add_member(
    db: AsyncSession, team_id: UUID, email: str, role: Role
) -> TeamMember:
    user = await get_user_by_email(db, email)
    if user is None:
        raise UserNotFound()
    if await db.get(TeamMember, (team_id, user.id)) is not None:
        raise AlreadyMember()
    member = TeamMember(team_id=team_id, user=user, role=role)
    db.add(member)
    await db.commit()
    return member

async def update_member_role(
    db: AsyncSession, team_id: UUID, user_id: UUID, role: Role
) -> TeamMember:
    member = await db.get(TeamMember, (team_id, user_id))
    if member is None:
        raise MemberNotFound()
    if member.role == Role.OWNER and role != Role.OWNER:
        if await _owner_count(db, team_id) <= 1:
            raise LastOwner()
    member.role = role
    await db.commit()
    return member

async def remove_member(
    db: AsyncSession, team_id: UUID, user_id: UUID
) -> None:
    member = await db.get(TeamMember, (team_id, user_id))
    if member is None:
        raise MemberNotFound()
    if member.role == Role.OWNER and await _owner_count(db, team_id) <= 1:
        raise LastOwner()
    await db.delete(member)
    await db.commit()

async def delete_team(db: AsyncSession, team_id: UUID) -> None:
    await db.execute(delete(Team).where(Team.id == team_id))
    await db.commit()