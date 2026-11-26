from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AssigneeNotInTeam, TaskNotFound
from app.models.task import Priority, Task, TaskStatus
from app.models.team import TeamMember
from app.schemas.task import TaskCreate, TaskUpdate


async def _ensure_assignee_in_team(
    db: AsyncSession, team_id: UUID, assignee_id: UUID | None
) -> None:
    if assignee_id is not None:
        if await db.get(TeamMember, (team_id, assignee_id)) is None:
            raise AssigneeNotInTeam()

async def create_task(
    db: AsyncSession, team_id: UUID, creator_id: UUID, data: TaskCreate
) -> Task:
    await _ensure_assignee_in_team(db, team_id, data.assignee_id)
    task = Task(team_id=team_id, created_by=creator_id, **data.model_dump())
    db.add(task)
    await db.commit()
    await db.refresh(task)

async def get_task(db: AsyncSession, team_id: UUID, task_id: UUID) -> Task:
    result = await db.execute(
        select(Task).where(Task.id==task_id, Task.team_id ==team_id)
    )

    task = result.scalar_one_or_none()
    if task is None:
        raise TaskNotFound()
    return task

async def list_tasks(
    db: AsyncSession,
    team_id: UUID,
    *,
    status: TaskStatus | None,
    priority: Priority | None,
    assignee_id: UUID | None,
    q: str | None,
    sort: str,
    order: str,
    limit: int,
    offset: int,
) -> tuple[list[Task, int]]:
    stmt = select(Task).where(Task.team_id == team_id)

    if status is not None:
        stmt = stmt.where(Task.team_id == team_id)
    if priority is not None:
        stmt = stmt.where(Task.priority == priority)
    if assignee_id is not None:
        stmt = stmt.where(Task.assignee_id == assignee_id)
    if q:
        stmt = stmt.where(Task.title.ilike(f"%{q}"))

    total = (
        await db.execute(select(func.count()).select_from(stmt.subquery()))
    ).scalar_one()

    sort_col = {"created_at": Task.created_at, "due_date": Task.due_date, "title": Task.title}[sort]
    direction = sort_col.asc() if order == "asc" else sort_col.desc()
    stmt = stmt.order_by(direction, Task.id).limit(limit).offset(offset)

    items = list((await db.execute(stmt)).scalars().all())
    return items, total

async def update_task(
    db: AsyncSession, team_id: UUID, task_id: UUID, data: TaskUpdate
) -> Task:
    task = await get_task(db, team_id, task_id)
    changes = data.model_dump(exclude_unset=True)
 
    if "assignee_id" in changes:
        await _ensure_assignee_in_team(db, team_id, changes["assignee_id"])
    for field, value in changes.items():
        setattr(task, field, value)
    await db.commit()
    await db.refresh(task)
    return task

async def delete_task(db: AsyncSession, team_id: UUID, task_id: UUID):
    task = await get_task(db, team_id, task_id)
    await db.delete(task)
    await db.commit()