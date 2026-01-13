'use client';

import { useParams } from 'next/navigation';
import Link from 'next/link';
import { useQuery } from '@tanstack/react-query';
import { ArrowLeftRight, Copy, Check } from 'lucide-react';
import { useState } from 'react';
import { fetchTransaction } from '@/lib/api';
import { formatNumber, formatCPC, getTxTypeColor } from '@/lib/utils';

export default function TransactionDetailPage() {
  const params = useParams();
  const txHash = params.id as string;
  const [copied, setCopied] = useState<string | null>(null);

  const { data: tx, isLoading, error } = useQuery({
    queryKey: ['transaction', txHash],
    queryFn: () => fetchTransaction(txHash),
  });

  const copyToClipboard = (text: string, field: string) => {
    navigator.clipboard.writeText(text);
    setCopied(field);
    setTimeout(() => setCopied(null), 2000);
  };

  if (isLoading) {
    return (
      <div className="animate-pulse space-y-6">
        <div className="h-8 bg-gray-200 dark:bg-slate-700 rounded w-1/4" />
        <div className="bg-white dark:bg-slate-800 rounded-xl p-6">
          <div className="space-y-4">
            {[...Array(10)].map((_, i) => (
              <div key={i} className="h-6 bg-gray-200 dark:bg-slate-700 rounded" />
            ))}
          </div>
        </div>
      </div>
    );
  }

  if (error || !tx) {
    return (
      <div className="text-center py-12">
        <h2 className="text-xl font-semibold text-gray-900 dark:text-white mb-2">Transaction Not Found</h2>
        <p className="text-gray-500">The transaction you're looking for doesn't exist.</p>
        <Link href="/transactions" className="text-primary-600 hover:text-primary-700 mt-4 inline-block">
          ← Back to transactions
        </Link>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center">
        <ArrowLeftRight className="w-8 h-8 text-primary-600 mr-3" />
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Transaction Details</h1>
          <p className="font-mono text-sm text-gray-500 break-all">{tx.hash}</p>
        </div>
      </div>

      {/* Transaction Details */}
      <div className="bg-white dark:bg-slate-800 rounded-xl shadow-sm border border-gray-100 dark:border-slate-700">
        <div className="p-6 space-y-4">
          <DetailRow
            label="Transaction Hash"
            value={tx.hash}
            mono
            copyable
            onCopy={() => copyToClipboard(tx.hash, 'hash')}
            copied={copied === 'hash'}
          />
          <DetailRow
            label="Status"
            value={
              <span className="px-2 py-1 rounded text-xs font-medium bg-green-100 text-green-800">
                Confirmed
              </span>
            }
          />
          <DetailRow
            label="Block"
            value={
              <Link href={`/blocks/${tx.block_height}`} className="text-primary-600 hover:text-primary-700">
                #{formatNumber(tx.block_height)}
              </Link>
            }
          />
          <DetailRow
            label="Type"
            value={
              <span className={`px-2 py-1 rounded text-xs font-medium ${getTxTypeColor(tx.tx_type)}`}>
                {tx.tx_type}
              </span>
            }
          />
          <DetailRow
            label="From"
            value={
              <Link href={`/accounts/${tx.from_address}`} className="text-primary-600 hover:text-primary-700 font-mono">
                {tx.from_address}
              </Link>
            }
          />
          {tx.to_address && (
            <DetailRow
              label="To"
              value={
                <Link href={`/accounts/${tx.to_address}`} className="text-primary-600 hover:text-primary-700 font-mono">
                  {tx.to_address}
                </Link>
              }
            />
          )}
          <DetailRow label="Amount" value={`${formatCPC(tx.amount)} CPC`} />
          <DetailRow label="Transaction Fee" value={`${formatCPC(tx.fee)} CPC`} />
          <DetailRow label="Nonce" value={tx.nonce.toString()} />

          {tx.gas_price !== undefined && (
            <>
              <DetailRow label="Gas Price" value={`${formatNumber(tx.gas_price)} wei`} />
              <DetailRow label="Gas Limit" value={formatNumber(tx.gas_limit || 0)} />
              <DetailRow label="Gas Used" value={formatNumber(tx.gas_used || 0)} />
            </>
          )}

          {tx.signature && (
            <DetailRow label="Signature" value={tx.signature} mono />
          )}

          {tx.pub_key && (
            <DetailRow label="Public Key" value={tx.pub_key} mono />
          )}

          {tx.payload && Object.keys(tx.payload).length > 0 && (
            <DetailRow
              label="Payload"
              value={
                <pre className="text-xs bg-gray-100 dark:bg-slate-700 p-2 rounded overflow-x-auto">
                  {JSON.stringify(tx.payload, null, 2)}
                </pre>
              }
            />
          )}
        </div>
      </div>
    </div>
  );
}

function DetailRow({
  label,
  value,
  mono = false,
  copyable = false,
  onCopy,
  copied = false,
}: {
  label: string;
  value: React.ReactNode;
  mono?: boolean;
  copyable?: boolean;
  onCopy?: () => void;
  copied?: boolean;
}) {
  return (
    <div className="flex flex-col sm:flex-row sm:items-start py-2 border-b border-gray-100 dark:border-slate-700 last:border-0">
      <div className="text-sm font-medium text-gray-500 dark:text-gray-400 sm:w-40 mb-1 sm:mb-0 flex-shrink-0">
        {label}
      </div>
      <div className={`flex-1 text-sm text-gray-900 dark:text-white ${mono ? 'font-mono break-all' : ''}`}>
        {value}
        {copyable && onCopy && (
          <button onClick={onCopy} className="ml-2 text-gray-400 hover:text-gray-600 inline-flex items-center">
            {copied ? <Check className="w-4 h-4 text-green-500" /> : <Copy className="w-4 h-4" />}
          </button>
        )}
      </div>
    </div>
  );
}
