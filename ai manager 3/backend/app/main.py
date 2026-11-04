import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from starlette.exceptions import HTTPException as StarletteHTTPException

from starlette.responses import RedirectResponse
from app.api.v1.router import api_router
from app.core.config import settings
from app.core.errors import AppException, error_response
from app.core.limiter import limiter
from app.db.seed import seed_default_categories
from app.db.session import AsyncSessionLocal, engine, Base

# Setup structured logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("finance_app")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Enforce production security key validation
    if settings.ENVIRONMENT.lower() == "production":
        settings.validate_production_keys()

    logger.info("Initializing database and seeding default categories...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSessionLocal() as session:
        await seed_default_categories(session)
    logger.info("Application startup complete.")
    yield
    logger.info("Application shutting down.")
    await engine.dispose()


app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Production-grade AI Personal Finance Manager API",
    version="1.0.0",
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url=f"{settings.API_V1_STR}/docs",
    redoc_url=f"{settings.API_V1_STR}/redoc",
    lifespan=lifespan,
)

# Attach rate limiter
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Promise 3: In-transit security middleware & HTTPS redirection
@app.middleware("http")
async def security_headers_and_https_middleware(request: Request, call_next):
    # Enforce HTTPS redirect in production
    if settings.ENVIRONMENT.lower() == "production":
        proto = request.headers.get("x-forwarded-proto", request.url.scheme)
        if proto != "https":
            https_url = request.url.replace(scheme="https")
            return RedirectResponse(url=str(https_url), status_code=status.HTTP_301_MOVED_PERMANENTLY)

    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    if settings.ENVIRONMENT.lower() == "production":
        response.headers["Strict-Transport-Security"] = "max-age=63072000; includeSubDomains; preload"
    return response

# CORS configuration locked to frontend origin
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Consistent error format handlers: {error: {code, message, details}}
@app.exception_handler(AppException)
async def app_exception_handler(request: Request, exc: AppException):
    return error_response(
        code=exc.code,
        message=exc.message,
        details=exc.details,
        status_code=exc.status_code,
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    formatted_errors = []
    for err in exc.errors():
        field = " -> ".join(str(loc) for loc in err.get("loc", []))
        formatted_errors.append({
            "field": field,
            "message": err.get("msg"),
            "type": err.get("type"),
        })
    return error_response(
        code="VALIDATION_ERROR",
        message="Request payload validation failed",
        details=formatted_errors,
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
    )


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    return error_response(
        code=f"HTTP_{exc.status_code}",
        message=str(exc.detail),
        status_code=exc.status_code,
    )


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    logger.exception(f"Unhandled error occurred: {exc}")
    return error_response(
        code="INTERNAL_SERVER_ERROR",
        message="An unexpected internal server error occurred",
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
    )


# Health check endpoint
@app.get("/health")
async def health_check():
    return {"status": "ok", "app": settings.PROJECT_NAME, "environment": settings.ENVIRONMENT}


# Mount API routers (both /api/v1 and alias /api/auth)
app.include_router(api_router, prefix=settings.API_V1_STR)
from app.api.v1.endpoints import auth
app.include_router(auth.router, prefix="/api")

