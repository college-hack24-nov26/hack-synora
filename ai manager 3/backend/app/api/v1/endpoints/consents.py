from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.dependencies import get_current_user
from app.db.session import get_db
from app.models.models import User
from app.services import consent_service

router = APIRouter(prefix="/consents", tags=["consents"])


class ConsentResponse(BaseModel):
    id: str
    consent_type: str
    granted: bool
    granted_at: datetime
    revoked_at: Optional[datetime] = None
    policy_version: str

    class Config:
        from_attributes = True


class GrantConsentRequest(BaseModel):
    consent_type: str = Field(..., description="sms_import or statement_upload")
    policy_version: str = Field("1.0", description="Policy version accepted")


class RevokeConsentRequest(BaseModel):
    consent_type: str = Field(..., description="sms_import or statement_upload")
    delete_data: bool = Field(False, description="Optionally delete previously imported data")


class RevokeConsentResponse(BaseModel):
    consent: ConsentResponse
    data_deleted: bool
    deleted_transactions: int


@router.get("", response_model=List[ConsentResponse])
async def list_consents(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    consents = await consent_service.get_user_consents(db, current_user.id)
    return consents


@router.post("", response_model=ConsentResponse, status_code=status.HTTP_201_CREATED)
async def grant_consent(
    payload: GrantConsentRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    consent = await consent_service.grant_consent(
        db=db,
        user_id=current_user.id,
        consent_type=payload.consent_type,
        policy_version=payload.policy_version,
    )
    return consent


@router.post("/revoke", response_model=RevokeConsentResponse)
async def revoke_consent_post(
    payload: RevokeConsentRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await consent_service.revoke_consent(
        db=db,
        user_id=current_user.id,
        consent_type=payload.consent_type,
        delete_data=payload.delete_data,
    )
    return result


@router.delete("/{consent_type}", response_model=RevokeConsentResponse)
async def revoke_consent_delete(
    consent_type: str,
    delete_data: bool = Query(False, description="Optionally delete previously imported data"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await consent_service.revoke_consent(
        db=db,
        user_id=current_user.id,
        consent_type=consent_type,
        delete_data=delete_data,
    )
    return result

