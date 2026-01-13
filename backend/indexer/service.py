"""Block indexer service."""
import asyncio
from datetime import datetime
from decimal import Decimal
from typing import Optional
import logging

from sqlalchemy import select, delete, func
from sqlalchemy.dialects.postgresql import insert

from core.config import get_settings
from core.database import get_session_context
from models import Block, Transaction, TxType, Account, SyncStatus
from .client import BlockchainClient

logger = logging.getLogger(__name__)
settings = get_settings()

# Batch size for parallel block fetching
BATCH_SIZE = 50


class IndexerService:
    """Service for indexing blockchain data."""

    def __init__(self):
        self.client = BlockchainClient()
        self.running = False
        self.last_resync_time = 0

    async def start(self):
        """Start the indexer."""
        self.running = True
        logger.info("Indexer started")

        while self.running:
            try:
                await self._sync_loop()
            except Exception as e:
                logger.error(f"Indexer error: {e}", exc_info=True)
                await asyncio.sleep(5)

    async def stop(self):
        """Stop the indexer."""
        self.running = False
        await self.client.close()
        logger.info("Indexer stopped")

    async def _sync_loop(self):
        """Main synchronization loop."""
        indexed_height = await self._get_indexed_height()
        chain_height = await self.client.get_block_height()

        if chain_height == 0:
            logger.warning("Cannot get chain height, node might be down")
            await asyncio.sleep(settings.indexer_poll_interval)
            return

        # Sync new blocks
        if indexed_height < chain_height:
            blocks_behind = chain_height - indexed_height
            logger.info(f"Behind by {blocks_behind} blocks ({indexed_height} -> {chain_height})")
            await self._sync_blocks_batch(indexed_height + 1, chain_height)
        else:
            logger.debug(f"In sync at height {indexed_height}")

        # Periodic resync check for reorgs
        current_time = asyncio.get_event_loop().time()
        if current_time - self.last_resync_time > settings.resync_interval:
            await self._check_reorg()
            self.last_resync_time = current_time

        await asyncio.sleep(settings.indexer_poll_interval)

    async def _get_indexed_height(self) -> int:
        """Get last indexed block height."""
        async with get_session_context() as session:
            result = await session.execute(
                select(SyncStatus).where(SyncStatus.key == "last_indexed_height")
            )
            status = result.scalar_one_or_none()
            return int(status.value) if status else 0

    async def _set_indexed_height(self, session, height: int):
        """Set last indexed block height (within existing session)."""
        stmt = insert(SyncStatus).values(
            key="last_indexed_height",
            value=str(height),
            updated_at=datetime.utcnow()
        ).on_conflict_do_update(
            index_elements=["key"],
            set_={"value": str(height), "updated_at": datetime.utcnow()}
        )
        await session.execute(stmt)

    async def _sync_blocks_batch(self, start_height: int, end_height: int):
        """Sync blocks in batches for better performance."""
        total = end_height - start_height + 1
        processed = 0

        for batch_start in range(start_height, end_height + 1, BATCH_SIZE):
            batch_end = min(batch_start + BATCH_SIZE - 1, end_height)

            # Fetch blocks in parallel
            tasks = [
                self.client.get_block(h)
                for h in range(batch_start, batch_end + 1)
            ]
            blocks_data = await asyncio.gather(*tasks, return_exceptions=True)

            # Filter successful fetches
            valid_blocks = []
            for i, block_data in enumerate(blocks_data):
                height = batch_start + i
                if isinstance(block_data, Exception):
                    logger.error(f"Failed to fetch block {height}: {block_data}")
                elif block_data is None:
                    logger.warning(f"Block {height} returned None")
                else:
                    valid_blocks.append(block_data)

            if not valid_blocks:
                logger.error(f"No valid blocks in batch {batch_start}-{batch_end}")
                break

            # Index batch in single transaction
            await self._index_blocks_batch(valid_blocks)
            processed += len(valid_blocks)

            logger.info(f"Indexed {processed}/{total} blocks (batch {batch_start}-{batch_end})")

            # Small delay to avoid overwhelming the node
            await asyncio.sleep(0.1)

    async def _index_blocks_batch(self, blocks_data: list[dict]):
        """Index multiple blocks in a single database transaction."""
        if not blocks_data:
            return

        async with get_session_context() as session:
            addresses_to_update = set()
            max_height = 0

            for block_data in blocks_data:
                header = block_data.get("header", {})
                txs = block_data.get("txs", [])
                height = header["height"]
                max_height = max(max_height, height)

                block_hash = self.client.compute_block_hash(block_data)

                # Create block record
                block = Block(
                    height=height,
                    hash=block_hash,
                    prev_hash=header.get("prev_hash", ""),
                    timestamp=header.get("timestamp", 0),
                    chain_id=header.get("chain_id", ""),
                    proposer_address=header.get("proposer_address", ""),
                    tx_root=header.get("tx_root", ""),
                    state_root=header.get("state_root", ""),
                    compute_root=header.get("compute_root"),
                    gas_used=header.get("gas_used", 0),
                    gas_limit=header.get("gas_limit", 0),
                    tx_count=len(txs),
                    zk_state_proof_hash=header.get("zk_state_proof_hash"),
                    zk_compute_proof_hash=header.get("zk_compute_proof_hash"),
                    pq_signature=block_data.get("pq_signature"),
                    pq_sig_scheme_id=block_data.get("pq_sig_scheme_id"),
                )
                session.add(block)

                # Index transactions
                for idx, tx_data in enumerate(txs):
                    tx_hash = self.client.compute_tx_hash(tx_data)
                    tx = Transaction(
                        hash=tx_hash,
                        block_height=height,
                        tx_type=TxType(tx_data.get("tx_type", "TRANSFER")),
                        from_address=tx_data.get("from_address", ""),
                        to_address=tx_data.get("to_address"),
                        amount=Decimal(str(tx_data.get("amount", 0))),
                        fee=Decimal(str(tx_data.get("fee", 0))),
                        nonce=tx_data.get("nonce", 0),
                        gas_price=tx_data.get("gas_price", 0),
                        gas_limit=tx_data.get("gas_limit", 0),
                        gas_used=tx_data.get("gas_limit", 0),
                        signature=tx_data.get("signature", ""),
                        pub_key=tx_data.get("pub_key", ""),
                        payload=tx_data.get("payload", {}),
                        tx_index=idx,
                    )
                    session.add(tx)

                    # Collect addresses for later batch update
                    if tx_data.get("from_address"):
                        addresses_to_update.add(tx_data.get("from_address"))
                    if tx_data.get("to_address"):
                        addresses_to_update.add(tx_data.get("to_address"))

            # Update indexed height
            await self._set_indexed_height(session, max_height)

            # Flush to get IDs
            await session.flush()

            # Update accounts in batch (lightweight - just mark last seen)
            if addresses_to_update:
                await self._update_accounts_batch(session, addresses_to_update, max_height)

    async def _update_accounts_batch(self, session, addresses: set[str], height: int):
        """Batch update accounts - lightweight version without HTTP calls."""
        now = datetime.utcnow()

        for address in addresses:
            # Just upsert minimal account info - balance will be fetched on-demand via API
            stmt = insert(Account).values(
                address=address,
                balance=Decimal("0"),  # Will be updated when account is viewed
                nonce=0,
                tx_count=0,
                tx_sent_count=0,
                tx_received_count=0,
                last_seen_height=height,
                last_seen_at=now,
                updated_at=now,
            ).on_conflict_do_update(
                index_elements=["address"],
                set_={
                    "last_seen_height": height,
                    "last_seen_at": now,
                    "updated_at": now,
                }
            )
            await session.execute(stmt)

    async def _check_reorg(self):
        """Check for chain reorganization in recent blocks."""
        logger.debug("Checking for reorgs...")

        indexed_height = await self._get_indexed_height()
        if indexed_height == 0:
            return

        check_from = max(1, indexed_height - settings.resync_depth)
        reorg_height = None

        async with get_session_context() as session:
            for height in range(indexed_height, check_from - 1, -1):
                result = await session.execute(
                    select(Block).where(Block.height == height)
                )
                indexed_block = result.scalar_one_or_none()
                if not indexed_block:
                    continue

                chain_block = await self.client.get_block(height)
                if not chain_block:
                    continue

                chain_hash = self.client.compute_block_hash(chain_block)

                if indexed_block.hash != chain_hash:
                    logger.warning(f"Reorg detected at height {height}!")
                    reorg_height = height
                    break

        if reorg_height:
            await self._handle_reorg(reorg_height)

    async def _handle_reorg(self, from_height: int):
        """Handle chain reorganization by resyncing from given height."""
        logger.info(f"Handling reorg from height {from_height}")

        async with get_session_context() as session:
            await session.execute(
                delete(Transaction).where(Transaction.block_height >= from_height)
            )
            await session.execute(
                delete(Block).where(Block.height >= from_height)
            )
            await self._set_indexed_height(session, from_height - 1)

        chain_height = await self.client.get_block_height()
        if chain_height >= from_height:
            await self._sync_blocks_batch(from_height, chain_height)


async def run_indexer():
    """Run the indexer service."""
    logger.info("Starting indexer service...")
    indexer = IndexerService()
    try:
        await indexer.start()
    except KeyboardInterrupt:
        await indexer.stop()
