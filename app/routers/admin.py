from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_superuser
from app.core.pagination import PaginationParams
from app.models.user import User
from app.schemas.user import UserRead

router = APIRouter(
    prefix="/admin",
    tags=["admin"],
    dependencies=[Depends(get_current_superuser)],
)

@router.get("/users", response_model=list[UserRead])
async def list_users(
    page: PaginationParams = Depends(),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(User).order_by(User.id).limit(page.limit).offset(page.offset)
    )
    return result.scalars().all()