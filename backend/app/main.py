import logging
import time
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pathlib import Path
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from app.config import settings
from app.routers import auth as auth_router
from app.routers import departments as dept_router
from app.routers import students as student_router
from app.routers import faculty as faculty_router
from app.routers import course_assignments as ca_router
from app.routers import timetable as tt_router
from app.routers import attendance as att_router
from app.routers import faculty_attendance as fatt_router
from app.routers import assignments as asgn_router
from app.routers import fees as fee_router
from app.routers import announcements as ann_router
from app.routers import certificates as cert_router
from app.routers import dashboard as dash_router
from app.routers import reports as report_router
from app.routers import ai as ai_router
from app.routers import hostel as hostel_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger("scms")

limiter = Limiter(key_func=get_remote_address)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("SCMS API starting up...")
    # Ensure uploads directories exist for local file storage
    for d in ["assignments", "submissions", "announcements", "certificates"]:
        Path(f"uploads/{d}").mkdir(parents=True, exist_ok=True)
    yield
    logger.info("SCMS API shutting down...")


app = FastAPI(
    title="Smart Campus Management System",
    description="Centralized platform for students, faculty, and administrators.",
    version="1.0.0",
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None,
    lifespan=lifespan,
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

_cors_origins = [o.strip() for o in settings.allowed_origins.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def request_logging_middleware(request: Request, call_next):
    request_id = str(uuid.uuid4())[:8]
    start = time.perf_counter()
    response = await call_next(request)
    elapsed = (time.perf_counter() - start) * 1000
    logger.info(
        f"[{request_id}] {request.method} {request.url.path} "
        f"→ {response.status_code} ({elapsed:.1f}ms)"
    )
    response.headers["X-Request-ID"] = request_id
    return response


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.exception(f"Unhandled error on {request.method} {request.url.path}: {exc}")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Internal server error"},
    )


# Routers
app.include_router(auth_router.router, prefix="/api/v1")
app.include_router(dept_router.router, prefix="/api/v1")
app.include_router(student_router.router, prefix="/api/v1")
app.include_router(faculty_router.router, prefix="/api/v1")
app.include_router(ca_router.router,   prefix="/api/v1")
app.include_router(tt_router.router,   prefix="/api/v1")
app.include_router(att_router.router,  prefix="/api/v1")
app.include_router(fatt_router.router, prefix="/api/v1")
app.include_router(asgn_router.router,     prefix="/api/v1")
app.include_router(asgn_router.sub_router, prefix="/api/v1")
app.include_router(fee_router.fs_router,          prefix="/api/v1")
app.include_router(fee_router.sf_router,          prefix="/api/v1")
app.include_router(fee_router.student_fee_router, prefix="/api/v1")
app.include_router(fee_router.receipt_router,     prefix="/api/v1")
app.include_router(ann_router.ann_router,         prefix="/api/v1")
app.include_router(ann_router.notif_router,       prefix="/api/v1")
app.include_router(cert_router.router,            prefix="/api/v1")
app.include_router(dash_router.router,            prefix="/api/v1")
app.include_router(report_router.router,          prefix="/api/v1")
app.include_router(ai_router.router,              prefix="/api/v1")
app.include_router(hostel_router.router,          prefix="/api/v1")


# Serve uploaded files as static assets
# e.g. GET /uploads/assignments/<id>/filename.pdf
uploads_dir = Path("uploads")
uploads_dir.mkdir(exist_ok=True)
app.mount("/uploads", StaticFiles(directory=str(uploads_dir)), name="uploads")


@app.get("/health", tags=["Health"])
async def health_check():
    return {"status": "ok", "app": settings.app_name, "env": settings.app_env}
