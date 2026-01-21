"""Account API endpoints."""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func, desc, or_
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from decimal import Decimal
from datetime import datetime
import asyncio
import httpx

from core.database import get_session
from core.config import get_settings
from models import Account, Transaction

router = APIRouter(prefix="/accounts", tags=["accounts"])
settings = get_settings()


async def fetch_balance_from_node(address: str) -> Optional[dict]:
    """Fetch account balance from blockchain node."""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(f"{settings.node_url}/balance/{address}")
            if resp.status_code == 200:
                return resp.json()
    except Exception:
        pass
    return None


async def fetch_balances_batch(addresses: list[str]) -> dict[str, dict]:
    """Fetch balances for multiple addresses in parallel."""
    if not addresses:
        return {}

    results: dict[str, dict] = {}
    async with httpx.AsyncClient(timeout=5.0) as client:
        tasks = [client.get(f"{settings.node_url}/balance/{address}") for address in addresses]
        responses = await asyncio.gather(*tasks, return_exceptions=True)

    for address, response in zip(addresses, responses):
        if isinstance(response, Exception):
            continue
        if response.status_code != 200:
            continue
        data = response.json()
        if isinstance(data, dict):
            results[address] = data

    return results


@router.get("")
async def get_accounts(
    page: int = Query(1, ge=1),
    limit: int = Query(settings.default_page_size, ge=1, le=settings.max_page_size),
    sort_by: str = Query("balance", description="Sort by: balance, tx_count, last_seen"),
    order: str = Query("desc", description="Order: asc or desc"),
    session: AsyncSession = Depends(get_session),
):
    """Get paginated list of accounts."""
    offset = (page - 1) * limit

    # Get total count
    count_result = await session.execute(select(func.count(Account.id)))
    total = count_result.scalar()

    # Build sort
    sort_column = {
        "balance": Account.balance,
        "tx_count": Account.tx_count,
        "last_seen": Account.last_seen_height,
    }.get(sort_by, Account.balance)

    order_func = desc if order == "desc" else lambda x: x

    # Get accounts
    result = await session.execute(
        select(Account)
        .order_by(order_func(sort_column))
        .offset(offset)
        .limit(limit)
    )
    accounts = result.scalars().all()

    # Refresh balances from node for the current page
    node_data = await fetch_balances_batch([account.address for account in accounts])
    if node_data:
        updated = False
        now = datetime.utcnow()
        for account in accounts:
            data = node_data.get(account.address)
            if not data:
                continue
            account.balance = Decimal(str(data.get("balance", 0)))
            account.nonce = data.get("nonce", account.nonce)
            account.updated_at = now
            updated = True
        if updated:
            await session.commit()

    return {
        "accounts": [_account_to_dict(a) for a in accounts],
        "pagination": {
            "page": page,
            "limit": limit,
            "total": total,
            "pages": (total + limit - 1) // limit if total > 0 else 0,
        }
    }


@router.get("/top")
async def get_top_accounts(
    limit: int = Query(10, ge=1, le=100),
    session: AsyncSession = Depends(get_session),
):
    """Get top accounts by balance."""
    result = await session.execute(
        select(Account)
        .order_by(desc(Account.balance))
        .limit(limit)
    )
    accounts = result.scalars().all()

    node_data = await fetch_balances_batch([account.address for account in accounts])
    if node_data:
        updated = False
        now = datetime.utcnow()
        for account in accounts:
            data = node_data.get(account.address)
            if not data:
                continue
            account.balance = Decimal(str(data.get("balance", 0)))
            account.nonce = data.get("nonce", account.nonce)
            account.updated_at = now
            updated = True
        if updated:
            await session.commit()

    return {"accounts": [_account_to_dict(a) for a in accounts]}


@router.get("/validators")
async def get_validators(
    session: AsyncSession = Depends(get_session),
):
    """Get all validator accounts."""
    result = await session.execute(
        select(Account)
        .where(Account.is_validator == True)
        .order_by(desc(Account.balance))
    )
    validators = result.scalars().all()

    node_data = await fetch_balances_batch([account.address for account in validators])
    if node_data:
        updated = False
        now = datetime.utcnow()
        for account in validators:
            data = node_data.get(account.address)
            if not data:
                continue
            account.balance = Decimal(str(data.get("balance", 0)))
            account.nonce = data.get("nonce", account.nonce)
            account.updated_at = now
            updated = True
        if updated:
            await session.commit()

    return {"validators": [_account_to_dict(a, include_validator_info=True) for a in validators]}


@router.get("/{address}")
async def get_account(
    address: str,
    session: AsyncSession = Depends(get_session),
):
    """Get account by address with live balance from node."""
    result = await session.execute(
        select(Account).where(Account.address == address)
    )
    account = result.scalar_one_or_none()

    # Fetch live balance from node
    node_data = await fetch_balance_from_node(address)

    if not account and not node_data:
        raise HTTPException(status_code=404, detail="Account not found")

    # Calculate tx counts from DB
    sent_result = await session.execute(
        select(func.count(Transaction.id)).where(Transaction.from_address == address)
    )
    sent_count = sent_result.scalar() or 0

    recv_result = await session.execute(
        select(func.count(Transaction.id)).where(Transaction.to_address == address)
    )
    recv_count = recv_result.scalar() or 0

    # If we have node data, update/create account with fresh balance
    if node_data:
        balance = Decimal(str(node_data.get("balance", 0)))
        nonce = node_data.get("nonce", 0)

        stmt = insert(Account).values(
            address=address,
            balance=balance,
            nonce=nonce,
            tx_count=sent_count + recv_count,
            tx_sent_count=sent_count,
            tx_received_count=recv_count,
            updated_at=datetime.utcnow(),
        ).on_conflict_do_update(
            index_elements=["address"],
            set_={
                "balance": balance,
                "nonce": nonce,
                "tx_count": sent_count + recv_count,
                "tx_sent_count": sent_count,
                "tx_received_count": recv_count,
                "updated_at": datetime.utcnow(),
            }
        )
        await session.execute(stmt)
        await session.commit()

        # Re-fetch updated account
        result = await session.execute(
            select(Account).where(Account.address == address)
        )
        account = result.scalar_one_or_none()

    return _account_to_dict(account, detailed=True)


@router.get("/{address}/transactions")
async def get_account_transactions(
    address: str,
    page: int = Query(1, ge=1),
    limit: int = Query(settings.default_page_size, ge=1, le=settings.max_page_size),
    direction: Optional[str] = Query(None, description="Filter: sent, received, or all"),
    session: AsyncSession = Depends(get_session),
):
    """Get transactions for an account."""
    offset = (page - 1) * limit

    # Build query based on direction
    if direction == "sent":
        query = select(Transaction).where(Transaction.from_address == address)
        count_query = select(func.count(Transaction.id)).where(Transaction.from_address == address)
    elif direction == "received":
        query = select(Transaction).where(Transaction.to_address == address)
        count_query = select(func.count(Transaction.id)).where(Transaction.to_address == address)
    else:
        query = select(Transaction).where(
            or_(Transaction.from_address == address, Transaction.to_address == address)
        )
        count_query = select(func.count(Transaction.id)).where(
            or_(Transaction.from_address == address, Transaction.to_address == address)
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
        "transactions": [
            {
                "hash": tx.hash,
                "block_height": tx.block_height,
                "tx_type": tx.tx_type.value,
                "from_address": tx.from_address,
                "to_address": tx.to_address,
                "amount": str(tx.amount),
                "fee": str(tx.fee),
                "nonce": tx.nonce,
                "direction": "sent" if tx.from_address == address else "received",
            }
            for tx in txs
        ],
        "pagination": {
            "page": page,
            "limit": limit,
            "total": total,
            "pages": (total + limit - 1) // limit if total > 0 else 0,
        }
    }


def _format_big_int(value) -> str:
    """Format large numbers without scientific notation."""
    if value is None:
        return "0"
    # Use format with 'f' to avoid scientific notation, then strip trailing zeros and decimal point
    return format(value, 'f').rstrip('0').rstrip('.')


def _account_to_dict(account: Account, detailed: bool = False, include_validator_info: bool = False) -> dict:
    """Convert account to dictionary."""
    data = {
        "address": account.address,
        "balance": _format_big_int(account.balance),
        "nonce": account.nonce,
        "tx_count": account.tx_count,
        "is_validator": account.is_validator,
    }

    if detailed:
        data.update({
            "tx_sent_count": account.tx_sent_count,
            "tx_received_count": account.tx_received_count,
            "first_seen_height": account.first_seen_height,
            "last_seen_height": account.last_seen_height,
            "first_seen_at": account.first_seen_at.isoformat() if account.first_seen_at else None,
            "last_seen_at": account.last_seen_at.isoformat() if account.last_seen_at else None,
        })

    if include_validator_info and account.validator_info:
        data["validator_info"] = account.validator_info

    return data
