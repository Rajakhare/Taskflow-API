import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy  import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import InvalidCredentials, InvalidToken
from app.core.security import (
    create_access_token,
    generate_refresh_token,
    hash_token,
    verify_password
)
from app.models.refresh_token import RefreshToken
from app.model.user import User
from app.services.user_service import get_user_by_email

async def authenticate_user(db: AsyncSession, email: str, password: str) -> User:
    user = await get_user_by_email(db, email)
    if user is None or not verify_password(password, user.password):
        raise InvalidCredentials()
    if not user.is_active:
        raise InvalidCredentials()
    return user


