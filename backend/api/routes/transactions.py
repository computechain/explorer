"""Transaction API endpoints."""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func, desc, or_
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from core.database import get_session
from core.config import get_settings
from models import Transaction, TxType

router = APIRouter(prefix="/transactions", tags=["transactions"])
settings = get_settings()


@router.get("")
async def get_transactions(
    page: int = Query(1, ge=1),
    limit: int = Query(settings.default_page_size, ge=1, le=settings.max_page_size),
    tx_type: Optional[str] = Query(None, description="Filter by transaction type"),
    address: Optional[str] = Query(None, description="Filter by address (from or to)"),
    session: AsyncSession = Depends(get_session),
):
    """Get paginated list of transactions."""
    offset = (page - 1) * limit

    # Build query
    query = select(Transaction)
    count_query = select(func.count(Transaction.id))

    if tx_type:
        try:
            tx_type_enum = TxType(tx_type)
            query = query.where(Transaction.tx_type == tx_type_enum)
            count_query = count_query.where(Transaction.tx_type == tx_type_enum)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid tx_type: {tx_type}")

    if address:
        query = query.where(
            or_(
                Transaction.from_address == address,
                Transaction.to_address == address
            )
        )
        count_query = count_query.where(
            or_(
                Transaction.from_address == address,
                Transaction.to_address == address
            )
        )

    # Get total count
    count_result = await session.execute(count_query)
    total = count_result.scalar()

    # Get transactions
    result = await session.execute(
        query
        .order_by(desc(Transaction.block_height), desc(Transaction.tx_index))
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
            "pages": (total + limit - 1) // limit if total > 0 else 0,
        }
    }


@router.get("/recent")
async def get_recent_transactions(
    limit: int = Query(10, ge=1, le=50),
    session: AsyncSession = Depends(get_session),
):
    """Get most recent transactions."""
    result = await session.execute(
        select(Transaction)
        .order_by(desc(Transaction.block_height), desc(Transaction.tx_index))
        .limit(limit)
    )
    txs = result.scalars().all()

    return {"transactions": [_tx_to_dict(tx) for tx in txs]}


@router.get("/types")
async def get_transaction_types():
    """Get available transaction types."""
    return {"types": [t.value for t in TxType]}


@router.get("/{hash}")
async def get_transaction(
    hash: str,
    session: AsyncSession = Depends(get_session),
):
    """Get transaction by hash."""
    result = await session.execute(
        select(Transaction).where(Transaction.hash == hash)
    )
    tx = result.scalar_one_or_none()

    if not tx:
        raise HTTPException(status_code=404, detail="Transaction not found")

    return _tx_to_dict(tx, detailed=True)


def _format_big_int(value) -> str:
    """Format large numbers without scientific notation."""
    if value is None:
        return "0"
    return format(value, 'f').rstrip('0').rstrip('.')


def _tx_to_dict(tx: Transaction, detailed: bool = False) -> dict:
    """Convert transaction to dictionary."""
    data = {
        "hash": tx.hash,
        "block_height": tx.block_height,
        "tx_type": tx.tx_type.value,
        "from_address": tx.from_address,
        "to_address": tx.to_address,
        "amount": _format_big_int(tx.amount),
        "fee": _format_big_int(tx.fee),
        "nonce": tx.nonce,
        "tx_index": tx.tx_index,
    }

    if detailed:
        data.update({
            "gas_price": tx.gas_price,
            "gas_limit": tx.gas_limit,
            "gas_used": tx.gas_used,
            "signature": tx.signature,
            "pub_key": tx.pub_key,
            "payload": tx.payload,
            "indexed_at": tx.indexed_at.isoformat() if tx.indexed_at else None,
        })

    return data
