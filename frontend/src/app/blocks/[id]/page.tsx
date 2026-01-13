'use client';

import { useParams } from 'next/navigation';
import Link from 'next/link';
import { useQuery } from '@tanstack/react-query';
import { Blocks, ArrowLeft, ArrowRight, Copy, Check } from 'lucide-react';
import { useState } from 'react';
import { fetchBlock } from '@/lib/api';
import { formatNumber, formatTimestamp, truncateAddress, truncateHash, formatCPC, getTxTypeColor } from '@/lib/utils';

export default function BlockDetailPage() {
  const params = useParams();
  const blockId = params.id as string;
  const [copied, setCopied] = useState<string | null>(null);

  const { data: block, isLoading, error } = useQuery({
    queryKey: ['block', blockId],
    queryFn: () => fetchBlock(blockId),
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
            {[...Array(8)].map((_, i) => (
              <div key={i} className="h-6 bg-gray-200 dark:bg-slate-700 rounded" />
            ))}
          </div>
        </div>
      </div>
    );
  }

  if (error || !block) {
    return (
      <div className="text-center py-12">
        <h2 className="text-xl font-semibold text-gray-900 dark:text-white mb-2">Block Not Found</h2>
        <p className="text-gray-500">The block you're looking for doesn't exist.</p>
        <Link href="/blocks" className="text-primary-600 hover:text-primary-700 mt-4 inline-block">
          ← Back to blocks
        </Link>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center">
          <Blocks className="w-8 h-8 text-primary-600 mr-3" />
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
            Block #{formatNumber(block.height)}
          </h1>
        </div>
        <div className="flex space-x-2">
          <Link
            href={`/blocks/${block.height - 1}`}
            className="px-3 py-2 rounded-lg border border-gray-300 dark:border-slate-600 hover:bg-gray-100 dark:hover:bg-slate-700 flex items-center"
          >
            <ArrowLeft className="w-4 h-4 mr-1" /> Prev
          </Link>
          <Link
            href={`/blocks/${block.height + 1}`}
            className="px-3 py-2 rounded-lg border border-gray-300 dark:border-slate-600 hover:bg-gray-100 dark:hover:bg-slate-700 flex items-center"
          >
            Next <ArrowRight className="w-4 h-4 ml-1" />
          </Link>
        </div>
      </div>

      {/* Block Details */}
      <div className="bg-white dark:bg-slate-800 rounded-xl shadow-sm border border-gray-100 dark:border-slate-700">
        <div className="p-6 space-y-4">
          <DetailRow label="Block Height" value={formatNumber(block.height)} />
          <DetailRow
            label="Block Hash"
            value={block.hash}
            mono
            copyable
            onCopy={() => copyToClipboard(block.hash, 'hash')}
            copied={copied === 'hash'}
          />
          <DetailRow label="Timestamp" value={formatTimestamp(block.timestamp)} />
          <DetailRow
            label="Proposer"
            value={
              <Link href={`/accounts/${block.proposer}`} className="text-primary-600 hover:text-primary-700 font-mono">
                {block.proposer}
              </Link>
            }
          />
          <DetailRow label="Transactions" value={`${block.tx_count} transactions`} />
          <DetailRow
            label="Gas Used"
            value={`${formatNumber(block.gas_used)} / ${formatNumber(block.gas_limit)} (${((block.gas_used / block.gas_limit) * 100).toFixed(1)}%)`}
          />
          <DetailRow label="State Root" value={block.state_root || '-'} mono />
          <DetailRow label="Tx Root" value={block.tx_root || '-'} mono />
          {block.prev_hash && (
            <DetailRow
              label="Parent Hash"
              value={
                <Link href={`/blocks/${block.height - 1}`} className="text-primary-600 hover:text-primary-700 font-mono">
                  {truncateHash(block.prev_hash, 20)}
                </Link>
              }
            />
          )}
        </div>
      </div>

      {/* Transactions */}
      {block.transactions && block.transactions.length > 0 && (
        <div className="bg-white dark:bg-slate-800 rounded-xl shadow-sm border border-gray-100 dark:border-slate-700">
          <div className="p-4 border-b border-gray-100 dark:border-slate-700">
            <h2 className="text-lg font-semibold text-gray-900 dark:text-white">
              Transactions ({block.transactions.length})
            </h2>
          </div>
          <div className="divide-y divide-gray-100 dark:divide-slate-700">
            {block.transactions.map((tx) => (
              <div key={tx.hash} className="p-4 hover:bg-gray-50 dark:hover:bg-slate-700/50">
                <div className="flex items-center justify-between">
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center space-x-2">
                      <Link
                        href={`/transactions/${tx.hash}`}
                        className="text-primary-600 hover:text-primary-700 font-mono text-sm"
                      >
                        {truncateHash(tx.hash)}
                      </Link>
                      <span className={`px-2 py-0.5 rounded text-xs font-medium ${getTxTypeColor(tx.tx_type)}`}>
                        {tx.tx_type}
                      </span>
                    </div>
                    <div className="text-sm text-gray-500 dark:text-gray-400 mt-1">
                      <Link href={`/accounts/${tx.from_address}`} className="font-mono hover:text-primary-600">
                        {truncateAddress(tx.from_address)}
                      </Link>
                      {tx.to_address && (
                        <>
                          <span className="mx-2">→</span>
                          <Link href={`/accounts/${tx.to_address}`} className="font-mono hover:text-primary-600">
                            {truncateAddress(tx.to_address)}
                          </Link>
                        </>
                      )}
                    </div>
                  </div>
                  <div className="text-right ml-4">
                    <div className="text-sm font-medium text-gray-900 dark:text-white">
                      {formatCPC(tx.amount)} CPC
                    </div>
                    <div className="text-xs text-gray-500">
                      Fee: {formatCPC(tx.fee)} CPC
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
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
    <div className="flex flex-col sm:flex-row sm:items-center py-2 border-b border-gray-100 dark:border-slate-700 last:border-0">
      <div className="text-sm font-medium text-gray-500 dark:text-gray-400 sm:w-40 mb-1 sm:mb-0">
        {label}
      </div>
      <div className={`flex-1 text-sm text-gray-900 dark:text-white ${mono ? 'font-mono break-all' : ''}`}>
        {value}
        {copyable && onCopy && (
          <button onClick={onCopy} className="ml-2 text-gray-400 hover:text-gray-600">
            {copied ? <Check className="w-4 h-4 text-green-500" /> : <Copy className="w-4 h-4" />}
          </button>
        )}
      </div>
    </div>
  );
}
