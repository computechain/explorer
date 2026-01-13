'use client';

import { useParams } from 'next/navigation';
import Link from 'next/link';
import { useQuery } from '@tanstack/react-query';
import { User, Copy, Check, ChevronLeft, ChevronRight } from 'lucide-react';
import { useState } from 'react';
import { fetchAccount, fetchAccountTransactions } from '@/lib/api';
import { formatNumber, formatCPC, truncateHash, getTxTypeColor } from '@/lib/utils';

export default function AccountDetailPage() {
  const params = useParams();
  const address = params.id as string;
  const [copied, setCopied] = useState(false);
  const [txPage, setTxPage] = useState(1);
  const [direction, setDirection] = useState<string>('');

  const { data: account, isLoading, error } = useQuery({
    queryKey: ['account', address],
    queryFn: () => fetchAccount(address),
  });

  const { data: txData, isLoading: txLoading } = useQuery({
    queryKey: ['account-transactions', address, txPage, direction],
    queryFn: () => fetchAccountTransactions(address, txPage, 25, direction || undefined),
  });

  const copyToClipboard = () => {
    navigator.clipboard.writeText(address);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  if (isLoading) {
    return (
      <div className="animate-pulse space-y-6">
        <div className="h-8 bg-gray-200 dark:bg-slate-700 rounded w-1/4" />
        <div className="bg-white dark:bg-slate-800 rounded-xl p-6">
          <div className="space-y-4">
            {[...Array(6)].map((_, i) => (
              <div key={i} className="h-6 bg-gray-200 dark:bg-slate-700 rounded" />
            ))}
          </div>
        </div>
      </div>
    );
  }

  if (error || !account) {
    return (
      <div className="text-center py-12">
        <h2 className="text-xl font-semibold text-gray-900 dark:text-white mb-2">Account Not Found</h2>
        <p className="text-gray-500">The account you're looking for doesn't exist.</p>
        <Link href="/accounts" className="text-primary-600 hover:text-primary-700 mt-4 inline-block">
          ← Back to accounts
        </Link>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center">
        <User className="w-8 h-8 text-primary-600 mr-3" />
        <div className="flex-1 min-w-0">
          <div className="flex items-center">
            <h1 className="text-2xl font-bold text-gray-900 dark:text-white mr-2">Account</h1>
            {account.is_validator && (
              <span className="px-2 py-1 rounded text-xs font-medium bg-purple-100 text-purple-800">
                Validator
              </span>
            )}
          </div>
          <div className="flex items-center mt-1">
            <p className="font-mono text-sm text-gray-500 truncate">{address}</p>
            <button onClick={copyToClipboard} className="ml-2 text-gray-400 hover:text-gray-600 flex-shrink-0">
              {copied ? <Check className="w-4 h-4 text-green-500" /> : <Copy className="w-4 h-4" />}
            </button>
          </div>
        </div>
      </div>

      {/* Account Overview */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="bg-white dark:bg-slate-800 rounded-xl shadow-sm border border-gray-100 dark:border-slate-700 p-6">
          <div className="text-sm text-gray-500 dark:text-gray-400 mb-1">Balance</div>
          <div className="text-2xl font-bold text-gray-900 dark:text-white">
            {formatCPC(account.balance)} CPC
          </div>
        </div>
        <div className="bg-white dark:bg-slate-800 rounded-xl shadow-sm border border-gray-100 dark:border-slate-700 p-6">
          <div className="text-sm text-gray-500 dark:text-gray-400 mb-1">Transactions</div>
          <div className="text-2xl font-bold text-gray-900 dark:text-white">
            {formatNumber(account.tx_count)}
          </div>
          <div className="text-xs text-gray-500 mt-1">
            Sent: {formatNumber(account.tx_sent_count || 0)} | Received: {formatNumber(account.tx_received_count || 0)}
          </div>
        </div>
        <div className="bg-white dark:bg-slate-800 rounded-xl shadow-sm border border-gray-100 dark:border-slate-700 p-6">
          <div className="text-sm text-gray-500 dark:text-gray-400 mb-1">Nonce</div>
          <div className="text-2xl font-bold text-gray-900 dark:text-white">
            {account.nonce}
          </div>
        </div>
      </div>

      {/* Transactions */}
      <div className="bg-white dark:bg-slate-800 rounded-xl shadow-sm border border-gray-100 dark:border-slate-700">
        <div className="flex items-center justify-between p-4 border-b border-gray-100 dark:border-slate-700">
          <h2 className="text-lg font-semibold text-gray-900 dark:text-white">Transactions</h2>
          <div className="flex space-x-2">
            {['', 'sent', 'received'].map((d) => (
              <button
                key={d}
                onClick={() => {
                  setDirection(d);
                  setTxPage(1);
                }}
                className={`px-3 py-1 rounded text-sm ${
                  direction === d
                    ? 'bg-primary-600 text-white'
                    : 'bg-gray-100 dark:bg-slate-700 text-gray-600 dark:text-gray-300 hover:bg-gray-200'
                }`}
              >
                {d === '' ? 'All' : d.charAt(0).toUpperCase() + d.slice(1)}
              </button>
            ))}
          </div>
        </div>

        <div className="divide-y divide-gray-100 dark:divide-slate-700">
          {txLoading ? (
            [...Array(5)].map((_, i) => (
              <div key={i} className="p-4 animate-pulse">
                <div className="h-4 bg-gray-200 dark:bg-slate-700 rounded w-1/3 mb-2" />
                <div className="h-3 bg-gray-200 dark:bg-slate-700 rounded w-1/2" />
              </div>
            ))
          ) : txData?.transactions?.length ? (
            txData.transactions.map((tx: any) => (
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
                      <span className={`px-2 py-0.5 rounded text-xs ${
                        tx.direction === 'sent' ? 'bg-red-100 text-red-700' : 'bg-green-100 text-green-700'
                      }`}>
                        {tx.direction === 'sent' ? 'OUT' : 'IN'}
                      </span>
                    </div>
                    <div className="text-sm text-gray-500 dark:text-gray-400 mt-1">
                      {tx.direction === 'sent' ? (
                        <>To: <span className="font-mono">{tx.to_address ? truncateHash(tx.to_address, 12) : '-'}</span></>
                      ) : (
                        <>From: <span className="font-mono">{truncateHash(tx.from_address, 12)}</span></>
                      )}
                    </div>
                  </div>
                  <div className="text-right ml-4">
                    <div className={`text-sm font-medium ${
                      tx.direction === 'sent' ? 'text-red-600' : 'text-green-600'
                    }`}>
                      {tx.direction === 'sent' ? '-' : '+'}{formatCPC(tx.amount)} CPC
                    </div>
                    <Link
                      href={`/blocks/${tx.block_height}`}
                      className="text-xs text-gray-500 hover:text-primary-600"
                    >
                      Block #{tx.block_height}
                    </Link>
                  </div>
                </div>
              </div>
            ))
          ) : (
            <div className="p-8 text-center text-gray-500">No transactions found</div>
          )}
        </div>

        {/* Pagination */}
        {txData?.pagination && txData.pagination.pages > 1 && (
          <div className="flex items-center justify-between px-4 py-3 border-t border-gray-100 dark:border-slate-700">
            <div className="text-sm text-gray-500">
              Page {txPage} of {txData.pagination.pages}
            </div>
            <div className="flex space-x-2">
              <button
                onClick={() => setTxPage(txPage - 1)}
                disabled={txPage === 1}
                className="px-2 py-1 rounded border border-gray-300 dark:border-slate-600 disabled:opacity-50"
              >
                <ChevronLeft className="w-4 h-4" />
              </button>
              <button
                onClick={() => setTxPage(txPage + 1)}
                disabled={txPage >= txData.pagination.pages}
                className="px-2 py-1 rounded border border-gray-300 dark:border-slate-600 disabled:opacity-50"
              >
                <ChevronRight className="w-4 h-4" />
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
