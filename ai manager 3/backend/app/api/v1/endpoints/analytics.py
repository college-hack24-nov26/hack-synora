from typing import List, Dict, Any
from fastapi import APIRouter, Depends, Request, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.dependencies import get_current_user
from app.core.limiter import limiter
from app.db.session import get_db
from app.models.models import User
from app.services import analytics_service, prediction_service, insight_service

router = APIRouter(prefix="/analytics", tags=["analytics"])


class UpdateSuggestionStatusRequest(BaseModel):
    status: str


@router.get("/summary")
@limiter.limit("60/minute")
async def get_summary(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await analytics_service.get_analytics_summary(db, current_user.id)


@router.get("/by-category")
@limiter.limit("60/minute")
async def get_by_category(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await analytics_service.get_spending_by_category(db, current_user.id)


@router.get("/forecast/current-month")
@limiter.limit("60/minute")
async def get_current_month_forecast(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Computes deterministic statistical monthly spending prediction for the current month
    based on past habits, current run-rate, unbilled recurring expenses, and outlier filtering.
    Also persists the result in the Forecast table.
    """
    prediction = await prediction_service.compute_monthly_prediction(db, current_user.id)
    # Persist in Forecast table
    await prediction_service.persist_prediction(db, current_user.id, prediction)
    return prediction


@router.get("/forecast/history")
@limiter.limit("60/minute")
async def get_forecast_history_endpoint(
    request: Request,
    months: int = Query(6, ge=1, le=24, description="Number of past months to include"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Returns monthly actuals vs predictions across previous months and current month.
    """
    return await prediction_service.get_forecast_history(db, current_user.id, months=months)


@router.get("/insights")
@limiter.limit("60/minute")
async def get_insights(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Returns 24h-cached AI-powered personalized spending insights & savings suggestions.
    """
    return await insight_service.get_or_generate_insights(db, current_user.id, force_refresh=False)


@router.post("/insights/refresh")
@limiter.limit("20/minute")
async def refresh_insights(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Forces immediate regeneration of spending insights and recommendations.
    """
    return await insight_service.get_or_generate_insights(db, current_user.id, force_refresh=True)


@router.patch("/insights/{suggestion_id}/status")
@limiter.limit("60/minute")
async def update_insight_status(
    request: Request,
    suggestion_id: str,
    payload: UpdateSuggestionStatusRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Updates suggestion status: 'accepted', 'dismissed', or 'new'.
    """
    return await insight_service.update_suggestion_status(
        db, current_user.id, suggestion_id, payload.status
    )
