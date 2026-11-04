from typing import Optional, List
from fastapi import APIRouter, Depends, Request, Response, Query, status
from fastapi.responses import PlainTextResponse
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.dependencies import require_admin
from app.core.limiter import limiter
from app.db.session import get_db
from app.models.models import User
from app.schemas.admin import (
    AdminOverviewResponse,
    AdminAnalyticsResponse,
    CustomerListResponse,
    Customer360Response,
    RiskAlert,
    AdminImportItem,
    AdminAuditLogItem,
    UpdateCustomerStatusRequest,
)
from app.services import admin_service, integration_health_service

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/overview", response_model=AdminOverviewResponse)
@limiter.limit("60/minute")
async def get_admin_overview(
    request: Request,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    overview = await admin_service.get_overview(db)
    client_ip = request.client.host if request.client else None
    await admin_service.log_admin_audit(
        db,
        admin_id=admin.id,
        action="ADMIN_VIEW_OVERVIEW",
        client_ip=client_ip,
    )
    return overview


@router.get("/analytics", response_model=AdminAnalyticsResponse)
@limiter.limit("60/minute")
async def get_admin_analytics(
    request: Request,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    analytics = await admin_service.get_analytics(db)
    client_ip = request.client.host if request.client else None
    await admin_service.log_admin_audit(
        db,
        admin_id=admin.id,
        action="ADMIN_VIEW_ANALYTICS",
        client_ip=client_ip,
    )
    return analytics


@router.get("/customers", response_model=CustomerListResponse)
@limiter.limit("60/minute")
async def list_admin_customers(
    request: Request,
    q: Optional[str] = Query(None, description="Search by name or email"),
    segment: Optional[str] = Query(None, description="Filter by segment"),
    status: Optional[str] = Query(None, description="Filter by active/inactive"),
    risk_flag: Optional[str] = Query(None, description="Filter by risk flag (flagged/clean/all)"),
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await admin_service.list_customers(
        db,
        q=q,
        segment=segment,
        status=status,
        risk_filter=risk_flag,
        page=page,
        limit=limit,
    )
    client_ip = request.client.host if request.client else None
    await admin_service.log_admin_audit(
        db,
        admin_id=admin.id,
        action="ADMIN_LIST_CUSTOMERS",
        client_ip=client_ip,
        meta_data={"query": q, "segment": segment, "status": status, "page": page},
    )
    return result


@router.get("/customers/{customer_id}", response_model=Customer360Response)
@limiter.limit("60/minute")
async def get_admin_customer_360(
    customer_id: str,
    request: Request,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    customer_360 = await admin_service.get_customer_360(
        db,
        customer_id=customer_id,
        page=page,
        limit=limit,
    )
    client_ip = request.client.host if request.client else None
    await admin_service.log_admin_audit(
        db,
        admin_id=admin.id,
        action="ADMIN_VIEW_CUSTOMER",
        entity_id=customer_id,
        client_ip=client_ip,
    )
    return customer_360


@router.get("/risk-alerts", response_model=List[RiskAlert])
@limiter.limit("60/minute")
async def get_admin_risk_alerts(
    request: Request,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    alerts = await admin_service.get_risk_alerts(db)
    client_ip = request.client.host if request.client else None
    await admin_service.log_admin_audit(
        db,
        admin_id=admin.id,
        action="ADMIN_VIEW_RISK_ALERTS",
        client_ip=client_ip,
    )
    return alerts


@router.get("/imports")
@limiter.limit("60/minute")
async def get_admin_imports(
    request: Request,
    status: Optional[str] = Query(None, description="Filter by status"),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    items, total = await admin_service.get_admin_imports(
        db,
        status_filter=status,
        page=page,
        limit=limit,
    )
    client_ip = request.client.host if request.client else None
    await admin_service.log_admin_audit(
        db,
        admin_id=admin.id,
        action="ADMIN_VIEW_IMPORTS",
        client_ip=client_ip,
    )
    return {"items": items, "total": total, "page": page, "limit": limit}


@router.get("/audit-log")
@limiter.limit("60/minute")
async def get_admin_audit_log(
    request: Request,
    action: Optional[str] = Query(None, description="Filter by action"),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    items, total = await admin_service.get_admin_audit_logs(
        db,
        action_filter=action,
        page=page,
        limit=limit,
    )
    return {"items": items, "total": total, "page": page, "limit": limit}


@router.get("/export/customers.csv")
@limiter.limit("20/minute")
async def export_customers_csv(
    request: Request,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    csv_data = await admin_service.generate_customers_csv(db)
    client_ip = request.client.host if request.client else None
    await admin_service.log_admin_audit(
        db,
        admin_id=admin.id,
        action="ADMIN_EXPORT_CUSTOMERS",
        client_ip=client_ip,
    )
    return PlainTextResponse(
        content=csv_data,
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="masked_customers_summary.csv"'},
    )


@router.get("/health/integrations")
@limiter.limit("30/minute")
async def get_integration_health(
    request: Request,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """
    Comprehensive health status of external integrations (Email, SMS, LLM).
    Reports provider configuration, operational status, and latency.
    """
    health_report = await integration_health_service.run_all_health_checks()
    client_ip = request.client.host if request.client else None
    await admin_service.log_admin_audit(
        db,
        admin_id=admin.id,
        action="ADMIN_VIEW_INTEGRATION_HEALTH",
        client_ip=client_ip,
        meta_data={"status": health_report["status"]},
    )
    return health_report


@router.patch("/customers/{customer_id}/status")
@limiter.limit("30/minute")
async def update_customer_status(
    customer_id: str,
    payload: UpdateCustomerStatusRequest,
    request: Request,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    client_ip = request.client.host if request.client else None
    updated = await admin_service.update_customer_status(
        db,
        customer_id=customer_id,
        is_active=payload.is_active,
        admin_id=admin.id,
        client_ip=client_ip,
    )
    return {
        "id": updated.id,
        "name": updated.name,
        "is_active": updated.is_active,
        "message": f"Customer account has been {'reactivated' if updated.is_active else 'deactivated'}.",
    }

