"""Statistics API endpoints."""
from fastapi import APIRouter, Depends
from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timedelta

from core.database import get_session
from models import Block, Transaction, Account, SyncStatus, TxType

router = APIRouter(prefix="/stats", tags=["statistics"])


def _format_big_int(value) -> str:
    """Format large numbers without scientific notation."""
    if value is None:
        return "0"
    return format(value, 'f').rstrip('0').rstrip('.')


@router.get("")
async def get_stats(session: AsyncSession = Depends(get_session)):
    """Get overall blockchain statistics."""
    # Block stats
    block_count = await session.execute(select(func.count(Block.id)))
    latest_block = await session.execute(
        select(Block).order_by(desc(Block.height)).limit(1)
    )

    # Transaction stats
    tx_count = await session.execute(select(func.count(Transaction.id)))

    # Account stats
    account_count = await session.execute(select(func.count(Account.id)))

    # Total value transferred
    total_transferred = await session.execute(
        select(func.sum(Transaction.amount)).where(Transaction.tx_type == TxType.TRANSFER)
    )

    # Total fees
    total_fees = await session.execute(select(func.sum(Transaction.fee)))

    # Sync status
    sync_status = await session.execute(
        select(SyncStatus).where(SyncStatus.key == "last_indexed_height")
    )

    block = latest_block.scalar_one_or_none()
    sync = sync_status.scalar_one_or_none()

    return {
        "blocks": {
            "total": block_count.scalar() or 0,
            "latest_height": block.height if block else 0,
            "latest_timestamp": block.timestamp if block else 0,
        },
        "transactions": {
            "total": tx_count.scalar() or 0,
            "total_transferred": _format_big_int(total_transferred.scalar() or 0),
            "total_fees": _format_big_int(total_fees.scalar() or 0),
        },
        "accounts": {
            "total": account_count.scalar() or 0,
        },
        "sync": {
            "indexed_height": int(sync.value) if sync else 0,
            "last_updated": sync.updated_at.isoformat() if sync else None,
        }
    }


@router.get("/tx-types")
async def get_tx_type_stats(session: AsyncSession = Depends(get_session)):
    """Get transaction counts by type."""
    result = await session.execute(
        select(Transaction.tx_type, func.count(Transaction.id))
        .group_by(Transaction.tx_type)
    )

    return {
        "tx_types": {
            row[0].value: row[1]
            for row in result.all()
        }
    }


@router.get("/tps")
async def get_tps_stats(session: AsyncSession = Depends(get_session)):
    """Get TPS statistics."""
    # Get blocks from last hour
    one_hour_ago = datetime.utcnow() - timedelta(hours=1)

    result = await session.execute(
        select(Block)
        .where(Block.indexed_at >= one_hour_ago)
        .order_by(Block.height)
    )
    blocks = result.scalars().all()

    if len(blocks) < 2:
        return {
            "current_tps": 0,
            "avg_tps_1h": 0,
            "avg_block_time": 0,
            "blocks_1h": len(blocks),
        }

    # Calculate stats
    total_txs = sum(b.tx_count for b in blocks)
    time_span = blocks[-1].timestamp - blocks[0].timestamp if blocks[-1].timestamp > blocks[0].timestamp else 1

    avg_tps = total_txs / time_span if time_span > 0 else 0
    avg_block_time = time_span / (len(blocks) - 1) if len(blocks) > 1 else 0

    # Current TPS (last 10 blocks)
    recent_blocks = blocks[-10:] if len(blocks) >= 10 else blocks
    if len(recent_blocks) >= 2:
        recent_txs = sum(b.tx_count for b in recent_blocks)
        recent_time = recent_blocks[-1].timestamp - recent_blocks[0].timestamp
        current_tps = recent_txs / recent_time if recent_time > 0 else 0
    else:
        current_tps = 0

    return {
        "current_tps": round(current_tps, 2),
        "avg_tps_1h": round(avg_tps, 2),
        "avg_block_time": round(avg_block_time, 2),
        "blocks_1h": len(blocks),
        "txs_1h": total_txs,
    }


@router.get("/chart/blocks")
async def get_block_chart(
    hours: int = 24,
    session: AsyncSession = Depends(get_session),
):
    """Get block production chart data."""
    since = datetime.utcnow() - timedelta(hours=hours)

    result = await session.execute(
        select(Block)
        .where(Block.indexed_at >= since)
        .order_by(Block.height)
    )
    blocks = result.scalars().all()

    # Group by hour
    hourly_data = {}
    for block in blocks:
        hour_key = datetime.fromtimestamp(block.timestamp).replace(minute=0, second=0, microsecond=0)
        if hour_key not in hourly_data:
            hourly_data[hour_key] = {"blocks": 0, "txs": 0, "gas": 0}
        hourly_data[hour_key]["blocks"] += 1
        hourly_data[hour_key]["txs"] += block.tx_count
        hourly_data[hour_key]["gas"] += block.gas_used

    return {
        "chart": [
            {
                "timestamp": int(hour.timestamp()),
                "hour": hour.isoformat(),
                "blocks": data["blocks"],
                "transactions": data["txs"],
                "gas_used": data["gas"],
            }
            for hour, data in sorted(hourly_data.items())
        ]
    }
