"""
FastAPI application entry point.
"""
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
from api.routes import webhook, calls, reports
from database.database import init_database
from services.scheduler_service import start_scheduler, shutdown_scheduler
from utils.logger import logger
from config.settings import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    # Startup
    logger.info("Starting AI Payment Caller application...")
    
    # Initialize database
    init_database()
    
    # Start scheduler
    start_scheduler()
    
    logger.info("Application started successfully")
    
    yield
    
    # Shutdown
    logger.info("Shutting down application...")
    shutdown_scheduler()
    logger.info("Application shut down")


# Create FastAPI app
app = FastAPI(
    title="AI Payment Caller API",
    description="Automated payment reminder system using AI voice agents",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Include routers
app.include_router(webhook.router, prefix="/vapi", tags=["Vapi Webhook"])
app.include_router(calls.router, prefix="/calls", tags=["Calls"])
app.include_router(reports.router, prefix="/reports", tags=["Reports"])


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "AI Payment Caller API",
        "status": "running",
        "version": "1.0.0"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "environment": settings.environment
    }


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler."""
    logger.error(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={
            "message": "Internal server error",
            "detail": str(exc) if not settings.is_production else "An error occurred"
        }
    )