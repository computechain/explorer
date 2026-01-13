"""Blockchain node client."""
import hashlib
import json
import httpx
from typing import Optional
import logging

from core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class BlockchainClient:
    """Client for interacting with blockchain node."""

    def __init__(self, node_url: Optional[str] = None):
        self.node_url = node_url or settings.node_url
        self.client = httpx.AsyncClient(timeout=30.0)

    async def close(self):
        """Close HTTP client."""
        await self.client.aclose()

    async def get_block_height(self) -> int:
        """Get current block height."""
        try:
            resp = await self.client.get(f"{self.node_url}/metrics")
            if resp.status_code == 200:
                # Parse Prometheus metrics
                for line in resp.text.split("\n"):
                    if line.startswith("computechain_block_height "):
                        return int(float(line.split()[1]))
            return 0
        except Exception as e:
            logger.error(f"Failed to get block height: {e}")
            return 0

    async def get_block(self, height: int) -> Optional[dict]:
        """Get block by height."""
        try:
            resp = await self.client.get(f"{self.node_url}/block/{height}")
            if resp.status_code == 200:
                return resp.json()
            return None
        except Exception as e:
            logger.error(f"Failed to get block {height}: {e}")
            return None

    async def get_latest_block(self) -> Optional[dict]:
        """Get latest block."""
        try:
            resp = await self.client.get(f"{self.node_url}/block/latest")
            if resp.status_code == 200:
                return resp.json()
            return None
        except Exception as e:
            logger.error(f"Failed to get latest block: {e}")
            return None

    async def get_account(self, address: str) -> Optional[dict]:
        """Get account balance and nonce."""
        try:
            resp = await self.client.get(f"{self.node_url}/balance/{address}")
            if resp.status_code == 200:
                return resp.json()
            return None
        except Exception as e:
            logger.error(f"Failed to get account {address}: {e}")
            return None

    async def get_validators(self) -> list[dict]:
        """Get all validators."""
        try:
            resp = await self.client.get(f"{self.node_url}/validators")
            if resp.status_code == 200:
                return resp.json()
            return []
        except Exception as e:
            logger.error(f"Failed to get validators: {e}")
            return []

    @staticmethod
    def compute_block_hash(block: dict) -> str:
        """Compute block hash from header."""
        header = block.get("header", {})
        # Create deterministic hash from header fields
        hash_input = json.dumps({
            "height": header.get("height"),
            "prev_hash": header.get("prev_hash"),
            "timestamp": header.get("timestamp"),
            "tx_root": header.get("tx_root"),
            "state_root": header.get("state_root"),
        }, sort_keys=True)
        return hashlib.sha256(hash_input.encode()).hexdigest()

    @staticmethod
    def compute_tx_hash(tx: dict) -> str:
        """Compute transaction hash."""
        # Create deterministic hash from tx fields
        hash_input = json.dumps({
            "tx_type": tx.get("tx_type"),
            "from_address": tx.get("from_address"),
            "to_address": tx.get("to_address"),
            "amount": tx.get("amount"),
            "nonce": tx.get("nonce"),
            "signature": tx.get("signature"),
        }, sort_keys=True)
        return hashlib.sha256(hash_input.encode()).hexdigest()
