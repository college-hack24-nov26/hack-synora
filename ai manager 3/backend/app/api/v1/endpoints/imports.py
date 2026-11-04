from typing import Optional
from fastapi import APIRouter, Depends, status, Request, UploadFile, File, Form
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from app.core.config import settings
from app.core.dependencies import get_current_user, get_owned_or_404
from app.core.limiter import limiter
from app.core.errors import NotFoundException, ForbiddenException, BadRequestException
from app.db.session import get_db
from app.models.models import User, Import
from app.services import transaction_service, consent_service

router = APIRouter(prefix="/imports", tags=["imports"])


class SmsImportRequest(BaseModel):
    account_id: str = Field(..., description="Target bank account ID")
    raw_text: str = Field(..., min_length=5, description="Raw bank SMS text blob")


class ImportResponse(BaseModel):
    id: str
    source_type: str
    file_name: Optional[str]
    status: str
    total_rows: int
    parsed_rows: int
    failed_rows: int
    error_report: list


@router.post("/sms")
@limiter.limit("20/minute")
async def import_sms(
    request: Request,
    payload: SmsImportRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # Enforce active consent for SMS ingestion (Promise 1)
    has_consent = await consent_service.has_active_consent(db, current_user.id, "sms_import")
    if not has_consent:
        raise ForbiddenException(
            message="Active consent for SMS import is required. Please grant permission before importing financial messages."
        )

    result = await transaction_service.process_sms_import(
        db=db,
        user_id=current_user.id,
        account_id=payload.account_id,
        raw_text=payload.raw_text,
    )
    return result


@router.post("/csv")
@limiter.limit("20/minute")
async def import_csv(
    request: Request,
    account_id: str = Form(..., description="Target bank account ID"),
    file: UploadFile = File(..., description="CSV statement file"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # Enforce active consent for Statement upload (Promise 1 & 6)
    has_consent = await consent_service.has_active_consent(db, current_user.id, "statement_upload")
    if not has_consent:
        raise ForbiddenException(
            message="Active consent for statement upload is required. Please grant permission before uploading statements."
        )

    # Validate file extension and MIME
    filename = file.filename or ""
    if not filename.lower().endswith((".csv", ".tsv", ".txt")):
        raise BadRequestException("Invalid file format. Please upload a .csv statement file.")

    # Read and enforce max size in memory
    content = await file.read()
    if len(content) > settings.MAX_UPLOAD_SIZE_BYTES:
        raise BadRequestException(f"File size exceeds the maximum limit of {settings.MAX_UPLOAD_SIZE_BYTES // (1024*1024)}MB.")

    result = await transaction_service.process_file_import(
        db=db,
        user_id=current_user.id,
        account_id=account_id,
        file_bytes=content,
        file_name=filename,
        source_type="csv",
    )
    return result


@router.post("/pdf")
@limiter.limit("20/minute")
async def import_pdf(
    request: Request,
    account_id: str = Form(..., description="Target bank account ID"),
    file: UploadFile = File(..., description="PDF statement file"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # Enforce active consent for Statement upload (Promise 1 & 6)
    has_consent = await consent_service.has_active_consent(db, current_user.id, "statement_upload")
    if not has_consent:
        raise ForbiddenException(
            message="Active consent for statement upload is required. Please grant permission before uploading statements."
        )

    # Validate file extension and MIME
    filename = file.filename or ""
    if not filename.lower().endswith(".pdf"):
        raise BadRequestException("Invalid file format. Please upload a .pdf bank statement.")

    # Read and enforce max size in memory
    content = await file.read()
    if len(content) > settings.MAX_UPLOAD_SIZE_BYTES:
        raise BadRequestException(f"File size exceeds the maximum limit of {settings.MAX_UPLOAD_SIZE_BYTES // (1024*1024)}MB.")

    result = await transaction_service.process_file_import(
        db=db,
        user_id=current_user.id,
        account_id=account_id,
        file_bytes=content,
        file_name=filename,
        source_type="pdf",
    )
    return result


@router.get("/{import_id}")
async def get_import_status(
    import_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await get_owned_or_404(db, Import, import_id, current_user.id)

