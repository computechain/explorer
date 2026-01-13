"""FastAPI application."""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging

from core.config import get_settings
from core.database import init_db
from .routes import blocks_router, transactions_router, accounts_router, stats_router

settings = get_settings()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s: %(message)s",
    datefmt="%H:%M:%S",
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    # Startup
    logging.info("Initializing database...")
    await init_db()
    logging.info("Database initialized")

    yield

    # Shutdown
    logging.info("Shutting down...")


app = FastAPI(
    title="ComputeChain Explorer API",
    description="API for ComputeChain blockchain explorer",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(blocks_router, prefix="/api")
app.include_router(transactions_router, prefix="/api")
app.include_router(accounts_router, prefix="/api")
app.include_router(stats_router, prefix="/api")


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "name": "ComputeChain Explorer API",
        "version": "1.0.0",
        "docs": "/docs",
    }


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy"}
