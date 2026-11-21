from fastapi import FastAPI, Depends
from sqlalchemy import text
from app.core.config import settings
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db


app = FastAPI(
    title=settings.app_name,
    debug=settings.debug
)

@app.get("/health")
async def health_check():
    return {"status": "ok"}

@app.get("/health/db")
async def health_db(db: AsyncSession = Depends(get_db)):
    await db.execute(text("SELECT 1"))
    return {"database": "connected"}