from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import EmailAlreadyExists
from app.core.security import hash_password
from app.models.user import User
from app.schemas.user import UserCreate

async def get_user_by_email(db: AsyncSession, email: str) -> User | None:
    result = await db.execute(select(User).where(User.email == email.lower()))
    return result.scalar_one_or_none()

async def create_user(db: AsyncSession, data: UserCreate) -> User:
    user = User(email=data.email.lower(), password_hash=hash_password(data.password))
    db.add(user)

    try: 
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise EmailAlreadyExists()
    await db.refresh(user)
    return user

    