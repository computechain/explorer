"""Block model."""
from datetime import datetime
from sqlalchemy import BigInteger, String, Integer, DateTime, Index
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.database import Base


class Block(Base):
    """Blockchain block."""

    __tablename__ = "blocks"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    height: Mapped[int] = mapped_column(BigInteger, unique=True, nullable=False, index=True)
    hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    prev_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    timestamp: Mapped[int] = mapped_column(BigInteger, nullable=False)
    chain_id: Mapped[str] = mapped_column(String(64), nullable=False)
    proposer_address: Mapped[str] = mapped_column(String(64), nullable=False, index=True)

    # Merkle roots
    tx_root: Mapped[str] = mapped_column(String(64), nullable=False)
    state_root: Mapped[str] = mapped_column(String(64), nullable=False)
    compute_root: Mapped[str] = mapped_column(String(64), nullable=True)

    # Gas
    gas_used: Mapped[int] = mapped_column(BigInteger, default=0)
    gas_limit: Mapped[int] = mapped_column(BigInteger, default=0)

    # Transaction count (denormalized for performance)
    tx_count: Mapped[int] = mapped_column(Integer, default=0)

    # ZK proofs (future)
    zk_state_proof_hash: Mapped[str] = mapped_column(String(64), nullable=True)
    zk_compute_proof_hash: Mapped[str] = mapped_column(String(64), nullable=True)

    # Post-quantum signature
    pq_signature: Mapped[str] = mapped_column(String(256), nullable=True)
    pq_sig_scheme_id: Mapped[int] = mapped_column(Integer, nullable=True)

    # Metadata
    indexed_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    transactions: Mapped[list["Transaction"]] = relationship(
        "Transaction", back_populates="block", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_blocks_timestamp", "timestamp"),
        Index("ix_blocks_proposer_height", "proposer_address", "height"),
    )

    def __repr__(self):
        return f"<Block height={self.height} hash={self.hash[:16]}...>"


# Import here to avoid circular imports
from .transaction import Transaction
