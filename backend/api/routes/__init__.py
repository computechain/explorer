"""API routes."""
from .blocks import router as blocks_router
from .transactions import router as transactions_router
from .accounts import router as accounts_router
from .stats import router as stats_router

__all__ = ["blocks_router", "transactions_router", "accounts_router", "stats_router"]
