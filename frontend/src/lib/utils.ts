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

function formatBigInt(value: bigint): string {
  const negative = value < 0n;
  const absValue = negative ? -value : value;
  const grouped = absValue.toString().replace(/\B(?=(\d{3})+(?!\d))/g, ',');
  return negative ? `-${grouped}` : grouped;
}

function parseBigInt(value: unknown): bigint {
  if (typeof value === 'bigint') return value;
  if (typeof value === 'number') {
    if (!Number.isFinite(value)) return 0n;
    return BigInt(Math.trunc(value));
  }
  if (typeof value !== 'string') return 0n;

  const trimmed = value.trim();
  if (trimmed === '') return 0n;
  if (/^-?\d+$/.test(trimmed)) return BigInt(trimmed);

  const expMatch = /^([+-])?(\d+)(?:\.(\d+))?[eE]([+-]?\d+)$/.exec(trimmed);
  if (expMatch) {
    const sign = expMatch[1] === '-' ? -1n : 1n;
    const intPart = expMatch[2];
    const fracPart = expMatch[3] || '';
    const exponent = parseInt(expMatch[4], 10);
    const digits = `${intPart}${fracPart}`.replace(/^0+/, '') || '0';
    const scale = exponent - fracPart.length;

    if (scale < 0) return 0n;
    return sign * BigInt(`${digits}${'0'.repeat(scale)}`);
  }

  return 0n;
}

export function formatNumber(num: number | string | bigint): string {
  if (typeof num === 'bigint') return formatBigInt(num);
  if (typeof num === 'number') {
    if (!Number.isFinite(num)) return '0';
    return num.toLocaleString('en-US');
  }

  const trimmed = num.trim();
  if (trimmed === '') return '0';
  if (/^-?\d+$/.test(trimmed)) return formatBigInt(BigInt(trimmed));

  const parsed = Number(trimmed);
  if (!Number.isFinite(parsed)) return '0';
  return parsed.toLocaleString('en-US');
}

export function formatCPC(amount: string | number | bigint, decimals: number = 18): string {
  const base = 10n ** BigInt(decimals);
  const value = parseBigInt(amount);
  const negative = value < 0n;
  const absValue = negative ? -value : value;
  const whole = absValue / base;
  const remainder = absValue % base;

  if (remainder === 0n) {
    return `${negative ? '-' : ''}${formatNumber(whole)}`;
  }

  const remainderStr = remainder.toString().padStart(decimals, '0');
  const trimmed = remainderStr.replace(/0+$/, '').slice(0, 6);
  if (trimmed === '') {
    return `${negative ? '-' : ''}${formatNumber(whole)}`;
  }

  return `${negative ? '-' : ''}${formatNumber(whole)}.${trimmed}`;
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
