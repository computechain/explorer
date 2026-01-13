"""Block API endpoints."""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from typing import Optional

from core.database import get_session
from core.config import get_settings
from models import Block, Transaction

router = APIRouter(prefix="/blocks", tags=["blocks"])
settings = get_settings()


@router.get("")
async def get_blocks(
    page: int = Query(1, ge=1),
    limit: int = Query(settings.default_page_size, ge=1, le=settings.max_page_size),
    session: AsyncSession = Depends(get_session),
):
    """Get paginated list of blocks."""
    offset = (page - 1) * limit

    # Get total count
    count_result = await session.execute(select(func.count(Block.id)))
    total = count_result.scalar()

    # Get blocks
    result = await session.execute(
        select(Block)
        .order_by(desc(Block.height))
        .offset(offset)
        .limit(limit)
    )
    blocks = result.scalars().all()

    return {
        "blocks": [
            {
                "height": b.height,
                "hash": b.hash,
                "timestamp": b.timestamp,
                "proposer": b.proposer_address,
                "tx_count": b.tx_count,
                "gas_used": b.gas_used,
                "gas_limit": b.gas_limit,
            }
            for b in blocks
        ],
        "pagination": {
            "page": page,
            "limit": limit,
            "total": total,
            "pages": (total + limit - 1) // limit,
        }
    }


@router.get("/latest")
async def get_latest_block(session: AsyncSession = Depends(get_session)):
    """Get latest block."""
    result = await session.execute(
        select(Block).order_by(desc(Block.height)).limit(1)
    )
    block = result.scalar_one_or_none()

    if not block:
        raise HTTPException(status_code=404, detail="No blocks found")

    return _block_to_dict(block)


@router.get("/{height_or_hash}")
async def get_block(
    height_or_hash: str,
    session: AsyncSession = Depends(get_session),
):
    """Get block by height or hash."""
    # Try to parse as height
    if height_or_hash.isdigit():
        result = await session.execute(
            select(Block)
            .options(selectinload(Block.transactions))
            .where(Block.height == int(height_or_hash))
        )
    else:
        result = await session.execute(
            select(Block)
            .options(selectinload(Block.transactions))
            .where(Block.hash == height_or_hash)
        )

    block = result.scalar_one_or_none()

    if not block:
        raise HTTPException(status_code=404, detail="Block not found")

    return _block_to_dict(block, include_txs=True)


@router.get("/{height}/transactions")
async def get_block_transactions(
    height: int,
    page: int = Query(1, ge=1),
    limit: int = Query(settings.default_page_size, ge=1, le=settings.max_page_size),
    session: AsyncSession = Depends(get_session),
):
    """Get transactions in a block."""
    offset = (page - 1) * limit

    # Check block exists
    block_result = await session.execute(
        select(Block).where(Block.height == height)
    )
    if not block_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Block not found")

    # Get total count
    count_result = await session.execute(
        select(func.count(Transaction.id)).where(Transaction.block_height == height)
    )
    total = count_result.scalar()

    # Get transactions
    result = await session.execute(
        select(Transaction)
        .where(Transaction.block_height == height)
        .order_by(Transaction.tx_index)
        .offset(offset)
        .limit(limit)
    )
    txs = result.scalars().all()

    return {
        "transactions": [_tx_to_dict(tx) for tx in txs],
        "pagination": {
            "page": page,
            "limit": limit,
            "total": total,
            "pages": (total + limit - 1) // limit,
        }
    }


def _block_to_dict(block: Block, include_txs: bool = False) -> dict:
    """Convert block to dictionary."""
    data = {
        "height": block.height,
        "hash": block.hash,
        "prev_hash": block.prev_hash,
        "timestamp": block.timestamp,
        "chain_id": block.chain_id,
        "proposer": block.proposer_address,
        "tx_root": block.tx_root,
        "state_root": block.state_root,
        "compute_root": block.compute_root,
        "gas_used": block.gas_used,
        "gas_limit": block.gas_limit,
        "tx_count": block.tx_count,
        "pq_signature": block.pq_signature,
        "pq_sig_scheme_id": block.pq_sig_scheme_id,
        "indexed_at": block.indexed_at.isoformat() if block.indexed_at else None,
    }

    if include_txs and block.transactions:
        data["transactions"] = [_tx_to_dict(tx) for tx in block.transactions]

    return data


def _tx_to_dict(tx: Transaction) -> dict:
    """Convert transaction to dictionary."""
    return {
        "hash": tx.hash,
        "block_height": tx.block_height,
        "tx_type": tx.tx_type.value,
        "from_address": tx.from_address,
        "to_address": tx.to_address,
        "amount": str(tx.amount),
        "fee": str(tx.fee),
        "nonce": tx.nonce,
        "gas_price": tx.gas_price,
        "gas_limit": tx.gas_limit,
        "tx_index": tx.tx_index,
    }
