"""Transaction model."""
from datetime import datetime
from decimal import Decimal
from sqlalchemy import BigInteger, String, Integer, DateTime, ForeignKey, Numeric, Index, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
import enum

from core.database import Base


class TxType(str, enum.Enum):
    """Transaction types."""
    TRANSFER = "TRANSFER"
    STAKE = "STAKE"
    UNSTAKE = "UNSTAKE"
    DELEGATE = "DELEGATE"
    UNDELEGATE = "UNDELEGATE"
    UPDATE_VALIDATOR = "UPDATE_VALIDATOR"
    UNJAIL = "UNJAIL"
    COMPUTE = "COMPUTE"
    SUBMIT_RESULT = "SUBMIT_RESULT"


class Transaction(Base):
    """Blockchain transaction."""

    __tablename__ = "transactions"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    block_height: Mapped[int] = mapped_column(BigInteger, ForeignKey("blocks.height", ondelete="CASCADE"), nullable=False)

    # Transaction type
    tx_type: Mapped[TxType] = mapped_column(SQLEnum(TxType), nullable=False, index=True)

    # Addresses
    from_address: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    to_address: Mapped[str] = mapped_column(String(64), nullable=True, index=True)

    # Values (using Numeric for large numbers)
    amount: Mapped[Decimal] = mapped_column(Numeric(78, 0), default=0)  # 78 digits for uint256
    fee: Mapped[Decimal] = mapped_column(Numeric(78, 0), default=0)
    nonce: Mapped[int] = mapped_column(BigInteger, nullable=False)

    # Gas
    gas_price: Mapped[int] = mapped_column(BigInteger, default=0)
    gas_limit: Mapped[int] = mapped_column(BigInteger, default=0)
    gas_used: Mapped[int] = mapped_column(BigInteger, default=0)

    # Signature
    signature: Mapped[str] = mapped_column(String(256), nullable=False)
    pub_key: Mapped[str] = mapped_column(String(128), nullable=False)

    # Payload (JSONB for flexible storage)
    payload: Mapped[dict] = mapped_column(JSONB, default=dict)

    # Position in block
    tx_index: Mapped[int] = mapped_column(Integer, default=0)

    # Metadata
    indexed_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    block: Mapped["Block"] = relationship("Block", back_populates="transactions")

    __table_args__ = (
        Index("ix_transactions_from_nonce", "from_address", "nonce"),
        Index("ix_transactions_block_index", "block_height", "tx_index"),
        Index("ix_transactions_type_height", "tx_type", "block_height"),
    )

    def __repr__(self):
        return f"<Transaction hash={self.hash[:16]}... type={self.tx_type}>"


# Import here to avoid circular imports
from .block import Block
