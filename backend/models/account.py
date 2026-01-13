"""Account model."""
from datetime import datetime
from decimal import Decimal
from sqlalchemy import BigInteger, String, DateTime, Numeric, Boolean, Index
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from core.database import Base


class Account(Base):
    """Blockchain account (address)."""

    __tablename__ = "accounts"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    address: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)

    # Balance (from last indexed state)
    balance: Mapped[Decimal] = mapped_column(Numeric(78, 0), default=0)
    nonce: Mapped[int] = mapped_column(BigInteger, default=0)

    # Statistics (denormalized for performance)
    tx_count: Mapped[int] = mapped_column(BigInteger, default=0)
    tx_sent_count: Mapped[int] = mapped_column(BigInteger, default=0)
    tx_received_count: Mapped[int] = mapped_column(BigInteger, default=0)

    # First/last activity
    first_seen_height: Mapped[int] = mapped_column(BigInteger, nullable=True)
    last_seen_height: Mapped[int] = mapped_column(BigInteger, nullable=True)
    first_seen_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)

    # Validator info (if validator)
    is_validator: Mapped[bool] = mapped_column(Boolean, default=False)
    validator_info: Mapped[dict] = mapped_column(JSONB, nullable=True)

    # Metadata
    indexed_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        Index("ix_accounts_balance", "balance"),
        Index("ix_accounts_tx_count", "tx_count"),
        Index("ix_accounts_is_validator", "is_validator"),
    )

    def __repr__(self):
        return f"<Account address={self.address[:16]}... balance={self.balance}>"


class SyncStatus(Base):
    """Indexer synchronization status."""

    __tablename__ = "sync_status"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    key: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    value: Mapped[str] = mapped_column(String(256), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<SyncStatus {self.key}={self.value}>"
