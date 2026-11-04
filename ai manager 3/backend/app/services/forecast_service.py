import uuid
from typing import List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.dependencies import get_owned_or_404
from app.models.models import Forecast, Category
from app.schemas.forecast import ForecastCreate


async def list_forecasts(db: AsyncSession, user_id: str) -> List[Forecast]:
    stmt = select(Forecast).where(Forecast.user_id == user_id).order_by(Forecast.target_month.desc())
    res = await db.execute(stmt)
    return list(res.scalars().all())


async def create_forecast(db: AsyncSession, user_id: str, req: ForecastCreate) -> Forecast:
    if req.category_id:
        await get_owned_or_404(db, Category, req.category_id, user_id, allow_system_read=True)

    forecast = Forecast(
        id=str(uuid.uuid4()),
        user_id=user_id,
        target_month=req.target_month,
        category_id=req.category_id,
        predicted_minor=req.predicted_minor,
        lower_bound_minor=req.lower_bound_minor,
        upper_bound_minor=req.upper_bound_minor,
        model_version=req.model_version or "v1-stat",
    )
    db.add(forecast)
    await db.commit()
    await db.refresh(forecast)
    return forecast


async def get_forecast(db: AsyncSession, user_id: str, forecast_id: str) -> Forecast:
    return await get_owned_or_404(db, Forecast, forecast_id, user_id)


async def delete_forecast(db: AsyncSession, user_id: str, forecast_id: str) -> None:
    forecast = await get_owned_or_404(db, Forecast, forecast_id, user_id)
    await db.delete(forecast)
    await db.commit()

