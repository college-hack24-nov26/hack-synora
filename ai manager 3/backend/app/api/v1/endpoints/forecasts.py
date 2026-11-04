from typing import List
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.dependencies import get_current_user
from app.db.session import get_db
from app.models.models import User
from app.schemas.forecast import ForecastCreate, ForecastResponse
from app.services import forecast_service

router = APIRouter(prefix="/forecasts", tags=["forecasts"])


@router.get("", response_model=List[ForecastResponse])
async def list_forecasts(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await forecast_service.list_forecasts(db, current_user.id)


@router.post("", response_model=ForecastResponse, status_code=status.HTTP_201_CREATED)
async def create_forecast(
    req: ForecastCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await forecast_service.create_forecast(db, current_user.id, req)


@router.get("/{forecast_id}", response_model=ForecastResponse)
async def get_forecast(
    forecast_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await forecast_service.get_forecast(db, current_user.id, forecast_id)


@router.delete("/{forecast_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_forecast(
    forecast_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await forecast_service.delete_forecast(db, current_user.id, forecast_id)
    return None

