import { clsx, type ClassValue } from 'clsx';

export function cn(...inputs: ClassValue[]) {
  return clsx(inputs);
}

export function truncateAddress(address: string, chars: number = 8): string {
  if (!address) return '';
  if (address.length <= chars * 2 + 3) return address;
  return `${address.slice(0, chars)}...${address.slice(-chars)}`;
}

export function truncateHash(hash: string, chars: number = 10): string {
  if (!hash) return '';
  if (hash.length <= chars + 3) return hash;
  return `${hash.slice(0, chars)}...`;
}

export function formatNumber(num: number | string): string {
  const n = typeof num === 'string' ? parseFloat(num) : num;
  if (isNaN(n)) return '0';
  return n.toLocaleString('en-US');
}

export function formatCPC(amount: string | number, decimals: number = 18): string {
  const wei = BigInt(amount.toString());
  const divisor = BigInt(10 ** decimals);
  const whole = wei / divisor;
  const remainder = wei % divisor;

  if (remainder === BigInt(0)) {
    return formatNumber(whole.toString());
  }

  const remainderStr = remainder.toString().padStart(decimals, '0');
  const trimmed = remainderStr.replace(/0+$/, '').slice(0, 4);

  if (trimmed === '') {
    return formatNumber(whole.toString());
  }

  return `${formatNumber(whole.toString())}.${trimmed}`;
}

export function formatTimestamp(timestamp: number): string {
  const date = new Date(timestamp * 1000);
  return date.toLocaleString();
}

export function formatTimeAgo(timestamp: number): string {
  const now = Date.now() / 1000;
  const diff = now - timestamp;

  if (diff < 60) return `${Math.floor(diff)}s ago`;
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
  if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
  return `${Math.floor(diff / 86400)}d ago`;
}

export function getTxTypeColor(txType: string): string {
  const colors: Record<string, string> = {
    TRANSFER: 'bg-blue-100 text-blue-800',
    STAKE: 'bg-green-100 text-green-800',
    UNSTAKE: 'bg-yellow-100 text-yellow-800',
    DELEGATE: 'bg-purple-100 text-purple-800',
    UNDELEGATE: 'bg-orange-100 text-orange-800',
    COMPUTE: 'bg-pink-100 text-pink-800',
    UNJAIL: 'bg-red-100 text-red-800',
  };
  return colors[txType] || 'bg-gray-100 text-gray-800';
}
