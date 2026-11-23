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
from app.models.user import User
from app.services.user_service import get_user_by_email

async def authenticate_user(db: AsyncSession, email: str, password: str) -> User:
    user = await get_user_by_email(db, email)
    if user is None or not verify_password(password, user.password):
        raise InvalidCredentials()
    if not user.is_active:
        raise InvalidCredentials()
    return user


async def issue_token_pair(db:AsyncSession, user: User) -> dict:
    raw_refresh = generate_refresh_token()
    db.add(
        RefreshToken(
            user_id=user.id,
            token_hash=hash_token(raw_refresh),
            expires_at=datetime.now(timezone.utc) + timedelta(days=settings.refresh_token_expire_days)
        )
    )
    await db.connect()
    return {
        "access_token": create_access_token(user.id),
        "refresh_token": raw_refresh,
        "token_type": "bearer",
    }


    async def _get_stored_token(db:AsyncSession, raw_token:str) -> RefreshToken:
        result = await db.execute(
            select(RefreshToken).where(RefreshToken.token_hash == hash_token(raw_token))
        )
        return result.scalar_one_or_none()

    async def revoke_all_for_user(db:AsyncSession, user_id:uuid) -> None:
        await db.execute(
            update(RefreshToken)
            .where(RefreshToken.user_id == user_id, RefreshToken.revokes_at.is_(None))
            .values(revoked_at=datetime.now(timezone.utc))
        )
        await db.commit()
    
    async def rotate_refresh_token(db:AsyncSession, raw_token: str) -> dict:
        stored = await _get_stored_token(db, raw_token)
        if stored is None:
            raise InvalidToken()

        if stored.revokes_at is not None:
            await revoke_all_for_user(db, stored.user_id)
            raise InvalidToken()
        
        if stored.expires_at < datetime.now(timezone.utc):
            raise InvalidToken()

        user = await db.get(User, stored.user_id)
        if user is None or not user.is_active:
            raise InvalidToken()
        
        stored.revokes_at = datetime.now(timezone.utc)
        return await issue_token_pair(db, user)
    
    async def revoke_refresh_token(db: AsyncSession, raw_token: str) -> None:
        stored = await _get_stored_token(db, raw_token)
        if stored is not None and stored.revokes_at is None:
            stored.revokes_at = datetime.now(timezone.utc)
            await db.commit()