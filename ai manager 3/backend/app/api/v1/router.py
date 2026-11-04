from fastapi import APIRouter
from app.api.v1.endpoints import (
    auth,
    accounts,
    categories,
    imports,
    transactions,
    analytics,
    consents,
    users,
    budgets,
    forecasts,
    merchant_rules,
    admin,
    assistant,
)

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(accounts.router)
api_router.include_router(categories.router)
api_router.include_router(imports.router)
api_router.include_router(transactions.router)
api_router.include_router(analytics.router)
api_router.include_router(consents.router)
api_router.include_router(users.router)
api_router.include_router(budgets.router)
api_router.include_router(forecasts.router)
api_router.include_router(merchant_rules.router)
api_router.include_router(admin.router)
api_router.include_router(assistant.router)
