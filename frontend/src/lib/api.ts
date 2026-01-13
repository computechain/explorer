const API_BASE = '/api';

async function fetchAPI<T>(endpoint: string): Promise<T> {
  const response = await fetch(`${API_BASE}${endpoint}`);
  if (!response.ok) {
    throw new Error(`API error: ${response.status}`);
  }
  return response.json();
}

// Stats
export interface Stats {
  blocks: {
    total: number;
    latest_height: number;
    latest_timestamp: number;
  };
  transactions: {
    total: number;
    total_transferred: string;
    total_fees: string;
  };
  accounts: {
    total: number;
  };
  sync: {
    indexed_height: number;
    last_updated: string | null;
  };
}

export function fetchStats(): Promise<Stats> {
  return fetchAPI<Stats>('/stats');
}

export function fetchTps(): Promise<{
  current_tps: number;
  avg_tps_1h: number;
  avg_block_time: number;
  blocks_1h: number;
  txs_1h: number;
}> {
  return fetchAPI('/stats/tps');
}

// Blocks
export interface Block {
  height: number;
  hash: string;
  timestamp: number;
  proposer: string;
  tx_count: number;
  gas_used: number;
  gas_limit: number;
  prev_hash?: string;
  chain_id?: string;
  tx_root?: string;
  state_root?: string;
  transactions?: Transaction[];
}

export interface BlocksResponse {
  blocks: Block[];
  pagination: Pagination;
}

export interface Pagination {
  page: number;
  limit: number;
  total: number;
  pages: number;
}

export function fetchBlocks(page: number = 1, limit: number = 25): Promise<BlocksResponse> {
  return fetchAPI<BlocksResponse>(`/blocks?page=${page}&limit=${limit}`);
}

export function fetchBlock(heightOrHash: string): Promise<Block> {
  return fetchAPI<Block>(`/blocks/${heightOrHash}`);
}

// Transactions
export interface Transaction {
  hash: string;
  block_height: number;
  tx_type: string;
  from_address: string;
  to_address: string | null;
  amount: string;
  fee: string;
  nonce: number;
  tx_index: number;
  gas_price?: number;
  gas_limit?: number;
  gas_used?: number;
  signature?: string;
  pub_key?: string;
  payload?: Record<string, unknown>;
}

export interface TransactionsResponse {
  transactions: Transaction[];
  pagination: Pagination;
}

export function fetchTransactions(
  page: number = 1,
  limit: number = 25,
  txType?: string,
  address?: string
): Promise<TransactionsResponse> {
  let url = `/transactions?page=${page}&limit=${limit}`;
  if (txType) url += `&tx_type=${txType}`;
  if (address) url += `&address=${address}`;
  return fetchAPI<TransactionsResponse>(url);
}

export function fetchRecentTransactions(limit: number = 10): Promise<TransactionsResponse> {
  return fetchAPI<TransactionsResponse>(`/transactions/recent?limit=${limit}`);
}

export function fetchTransaction(hash: string): Promise<Transaction> {
  return fetchAPI<Transaction>(`/transactions/${hash}`);
}

// Accounts
export interface Account {
  address: string;
  balance: string;
  nonce: number;
  tx_count: number;
  is_validator: boolean;
  tx_sent_count?: number;
  tx_received_count?: number;
  first_seen_height?: number;
  last_seen_height?: number;
}

export interface AccountsResponse {
  accounts: Account[];
  pagination: Pagination;
}

export function fetchAccounts(
  page: number = 1,
  limit: number = 25,
  sortBy: string = 'balance',
  order: string = 'desc'
): Promise<AccountsResponse> {
  return fetchAPI<AccountsResponse>(`/accounts?page=${page}&limit=${limit}&sort_by=${sortBy}&order=${order}`);
}

export function fetchAccount(address: string): Promise<Account> {
  return fetchAPI<Account>(`/accounts/${address}`);
}

export function fetchAccountTransactions(
  address: string,
  page: number = 1,
  limit: number = 25,
  direction?: string
): Promise<TransactionsResponse> {
  let url = `/accounts/${address}/transactions?page=${page}&limit=${limit}`;
  if (direction) url += `&direction=${direction}`;
  return fetchAPI<TransactionsResponse>(url);
}

export function fetchTopAccounts(limit: number = 10): Promise<{ accounts: Account[] }> {
  return fetchAPI<{ accounts: Account[] }>(`/accounts/top?limit=${limit}`);
}
