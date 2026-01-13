'use client';

import Link from 'next/link';
import { ArrowLeftRight, ArrowRight } from 'lucide-react';
import { Transaction } from '@/lib/api';
import { truncateHash, truncateAddress, formatCPC, getTxTypeColor } from '@/lib/utils';

interface RecentTransactionsProps {
  transactions?: Transaction[];
  loading?: boolean;
}

export function RecentTransactions({ transactions, loading }: RecentTransactionsProps) {
  return (
    <div className="bg-white dark:bg-slate-800 rounded-xl shadow-sm border border-gray-100 dark:border-slate-700">
      <div className="flex items-center justify-between p-4 border-b border-gray-100 dark:border-slate-700">
        <div className="flex items-center">
          <ArrowLeftRight className="w-5 h-5 text-primary-600 mr-2" />
          <h2 className="text-lg font-semibold text-gray-900 dark:text-white">
            Recent Transactions
          </h2>
        </div>
        <Link
          href="/transactions"
          className="text-sm text-primary-600 hover:text-primary-700 flex items-center"
        >
          View all <ArrowRight className="w-4 h-4 ml-1" />
        </Link>
      </div>

      <div className="divide-y divide-gray-100 dark:divide-slate-700">
        {loading ? (
          [...Array(5)].map((_, i) => (
            <div key={i} className="p-4 animate-pulse">
              <div className="h-4 bg-gray-200 dark:bg-slate-700 rounded w-1/3 mb-2" />
              <div className="h-3 bg-gray-200 dark:bg-slate-700 rounded w-1/2" />
            </div>
          ))
        ) : transactions?.length ? (
          transactions.map((tx) => (
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
                  <div className="text-sm text-gray-500 dark:text-gray-400 mt-1 truncate">
                    <span className="font-mono">{truncateAddress(tx.from_address)}</span>
                    {tx.to_address && (
                      <>
                        <span className="mx-2">→</span>
                        <span className="font-mono">{truncateAddress(tx.to_address)}</span>
                      </>
                    )}
                  </div>
                </div>
                <div className="text-right ml-4">
                  <div className="text-sm font-medium text-gray-900 dark:text-white">
                    {formatCPC(tx.amount)} CPC
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
    </div>
  );
}
