"""Main entry point for the explorer backend."""
import asyncio
import uvicorn
import logging
from multiprocessing import Process

from core.config import get_settings
from core.database import init_db
from api.app import app
from indexer.service import run_indexer

settings = get_settings()
logger = logging.getLogger(__name__)


def run_api():
    """Run the API server."""
    uvicorn.run(
        "explorer.backend.api.app:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=False,
        log_level="info",
    )


async def run_all():
    """Run both API and indexer."""
    # Initialize database
    await init_db()

    # Run indexer in background
    indexer_task = asyncio.create_task(run_indexer())

    # Run API in separate process
    api_process = Process(target=run_api)
    api_process.start()

    try:
        await indexer_task
    except KeyboardInterrupt:
        logger.info("Shutting down...")
    finally:
        api_process.terminate()
        api_process.join()


if __name__ == "__main__":
    asyncio.run(run_all())
