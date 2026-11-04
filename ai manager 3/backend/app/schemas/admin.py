from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, ConfigDict


class AdminOverviewResponse(BaseModel):
    total_customers: int
    active_customers_30d: int
    total_tracked_spend_this_month: int  # in paise
    avg_monthly_spend_per_customer: int  # in paise
    total_transactions: int
    import_success_rate: float  # e.g. 96.5%
    consented_customers_count: int
    demo_customers_count: int
    top_risk_customers: List[Dict[str, Any]] = []


class CategorySpendSummary(BaseModel):
    category_id: Optional[str] = None
    category_name: str
    icon: Optional[str] = "Tag"
    color: Optional[str] = "#3B82F6"
    total_spend_minor: int
    percentage: float


class MonthlySpendTrend(BaseModel):
    month: str  # YYYY-MM
    spend_minor: int
    transactions_count: int


class CustomerSegmentSummary(BaseModel):
    segment: str
    customer_count: int
    total_spend_minor: int


class MerchantSummary(BaseModel):
    merchant: str
    total_spend_minor: int
    transaction_count: int


class AdminAnalyticsResponse(BaseModel):
    spend_by_category: List[CategorySpendSummary]
    monthly_spend_trend: List[MonthlySpendTrend]
    customer_segments: List[CustomerSegmentSummary]
    top_merchants: List[MerchantSummary]


class CustomerSummaryItem(BaseModel):
    id: str
    name: str
    masked_email: str
    segment: Optional[str] = None
    accounts_count: int
    this_month_spend_minor: int
    predicted_month_end_spend_minor: int
    last_activity: Optional[datetime] = None
    is_active: bool
    is_demo: bool
    consent_type: Optional[str] = None
    risk_flags: List[str] = []


class CustomerListResponse(BaseModel):
    items: List[CustomerSummaryItem]
    total: int
    page: int
    limit: int


class CustomerProfile(BaseModel):
    id: str
    name: str
    masked_email: str
    currency: str
    timezone: str
    segment: Optional[str] = None
    is_active: bool
    is_demo: bool
    created_at: datetime


class AccountSummary(BaseModel):
    id: str
    name: str
    type: str
    masked_account_number: str
    opening_balance_minor: int
    current_balance_minor: int


class CustomerTransactionItem(BaseModel):
    id: str
    txn_date: datetime
    merchant_normalized: Optional[str]
    amount_minor: int
    direction: str
    currency: str
    category_name: Optional[str]
    category_icon: Optional[str]
    category_color: Optional[str]
    category_source: str
    category_confidence: float
    source: str
    needs_review: bool


class BudgetVsActual(BaseModel):
    category_id: str
    category_name: str
    month: str
    limit_minor: int
    actual_spent_minor: int
    status: str  # normal, warning, exceeded


class PredictionBreakdown(BaseModel):
    predicted_month_end_minor: int
    spent_so_far_minor: int
    days_elapsed: int
    days_in_month: int
    confidence_level: str
    historical_baseline_minor: int
    run_rate_projection_minor: int


class ConsentSummary(BaseModel):
    id: str
    consent_type: str
    granted: bool
    granted_at: datetime
    revoked_at: Optional[datetime] = None
    policy_version: str


class ImportSummary(BaseModel):
    id: str
    source_type: str
    status: str
    total_rows: int
    parsed_rows: int
    failed_rows: int
    error_summary: Optional[str] = None
    created_at: datetime


class Customer360Response(BaseModel):
    profile: CustomerProfile
    accounts: List[AccountSummary]
    transactions: List[CustomerTransactionItem]
    total_transactions: int
    category_breakdown: List[CategorySpendSummary]
    monthly_trend: List[MonthlySpendTrend]
    budgets: List[BudgetVsActual]
    prediction: Optional[PredictionBreakdown] = None
    consent_status: List[ConsentSummary]
    imports: List[ImportSummary]


class RiskAlert(BaseModel):
    id: str
    customer_id: str
    customer_name: str
    masked_email: str
    segment: Optional[str] = None
    alert_type: str
    severity: str  # high, medium, low
    reason: str
    detected_at: datetime


class AdminImportItem(BaseModel):
    id: str
    customer_id: str
    customer_name: str
    masked_email: str
    source_type: str
    status: str
    total_rows: int
    parsed_rows: int
    failed_rows: int
    error_summary: Optional[str] = None
    created_at: datetime


class AdminAuditLogItem(BaseModel):
    id: str
    admin_id: str
    admin_email: str
    action: str
    customer_id: Optional[str] = None
    customer_name: Optional[str] = None
    timestamp: datetime
    ip_address: Optional[str] = None
    details: Optional[Dict[str, Any]] = None


class UpdateCustomerStatusRequest(BaseModel):
    is_active: bool

