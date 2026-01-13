# ComputeChain Explorer

Blockchain explorer for ComputeChain.

## Quick Start

```bash
# Start explorer (PostgreSQL + Backend + Frontend)
docker-compose up -d

# View logs
docker-compose logs -f

# Stop
docker-compose down
```

**URLs:**
- Frontend: http://localhost:3000
- API: http://localhost:3001
- API Docs: http://localhost:3001/docs

## Requirements

- Docker & Docker Compose
- Running ComputeChain node on `localhost:8000`

## Configuration

Environment variables in `docker-compose.yml`:

| Variable | Default | Description |
|----------|---------|-------------|
| `EXPLORER_NODE_URL` | `http://host.docker.internal:8000` | Blockchain node URL |
| `EXPLORER_INDEXER_POLL_INTERVAL` | `2` | Sync interval (seconds) |
| `EXPLORER_RESYNC_INTERVAL` | `300` | Reorg check interval (seconds) |
| `EXPLORER_RESYNC_DEPTH` | `10` | Blocks to check for reorg |

## Architecture

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  Frontend   │────▶│   Backend   │────▶│  PostgreSQL │
│  Next.js    │     │   FastAPI   │     │             │
│  :3000      │     │   :3001     │     │   :5432     │
└─────────────┘     └──────┬──────┘     └─────────────┘
                          │
                          ▼
                   ┌─────────────┐
                   │  Blockchain │
                   │    Node     │
                   │   :8000     │
                   └─────────────┘
```

## Features

- **Real-time Indexing**: Syncs blocks as they're produced
- **Reorg Detection**: Verifies last N blocks every 5 minutes
- **Dashboard**: Stats, TPS, recent activity
- **Block Explorer**: Browse blocks with transactions
- **Transaction Explorer**: Filter by type, address
- **Account Explorer**: Balances, transaction history
- **Search**: By block height, tx hash, or address

## Development

```bash
# Run without Docker (for development)

# 1. PostgreSQL
docker run -d --name explorer-db \
  -e POSTGRES_USER=explorer \
  -e POSTGRES_PASSWORD=explorer \
  -e POSTGRES_DB=explorer \
  -p 5432:5432 \
  postgres:16-alpine

# 2. Backend
cd backend
pip install -r requirements.txt
python -m backend.main

# 3. Frontend
cd frontend
npm install
npm run dev
```

## API Endpoints

### Blocks
- `GET /api/blocks` - List blocks
- `GET /api/blocks/{height}` - Block details

### Transactions
- `GET /api/transactions` - List transactions
- `GET /api/transactions/{hash}` - Transaction details

### Accounts
- `GET /api/accounts` - List accounts
- `GET /api/accounts/{address}` - Account details

### Stats
- `GET /api/stats` - Overview statistics
- `GET /api/stats/tps` - TPS metrics
