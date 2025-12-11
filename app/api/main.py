"""FastAPI application."""

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.routes import router
from app.config import settings

app = FastAPI(
    title="SkyPlanner API",
    description="Weather and Schedule Planning Assistant API",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routes
app.include_router(router)


# Exception handlers
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Global exception handler."""
    if settings.debug:
        return JSONResponse(
            status_code=500,
            content={"error": "Internal server error", "detail": str(exc)},
        )
    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error"},
    )


# Health check
@app.get("/health")
async def health_check() -> dict:
    """Health check endpoint."""
    return {"status": "healthy"}


@app.get("/")
async def root() -> dict:
    """Root endpoint."""
    return {
        "name": "SkyPlanner API",
        "version": "0.1.0",
        "docs": "/docs",
    }