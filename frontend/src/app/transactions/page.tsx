'use client';

import { useState } from 'react';
import Link from 'next/link';
import { useQuery } from '@tanstack/react-query';
import { ArrowLeftRight, ChevronLeft, ChevronRight, Filter } from 'lucide-react';
import { fetchTransactions } from '@/lib/api';
import { formatNumber, truncateHash, truncateAddress, formatCPC, getTxTypeColor } from '@/lib/utils';

const TX_TYPES = ['TRANSFER', 'STAKE', 'UNSTAKE', 'DELEGATE', 'UNDELEGATE', 'COMPUTE', 'UNJAIL'];

export default function TransactionsPage() {
  const [page, setPage] = useState(1);
  const [txType, setTxType] = useState<string>('');
  const limit = 25;

  const { data, isLoading } = useQuery({
    queryKey: ['transactions', page, txType],
    queryFn: () => fetchTransactions(page, limit, txType || undefined),
  });

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center">
          <ArrowLeftRight className="w-8 h-8 text-primary-600 mr-3" />
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Transactions</h1>
        </div>

        {/* Filter */}
        <div className="flex items-center space-x-2">
          <Filter className="w-4 h-4 text-gray-500" />
          <select
            value={txType}
            onChange={(e) => {
              setTxType(e.target.value);
              setPage(1);
            }}
            className="px-3 py-2 border border-gray-300 dark:border-slate-600 rounded-lg text-sm bg-white dark:bg-slate-800"
          >
            <option value="">All Types</option>
            {TX_TYPES.map((type) => (
              <option key={type} value={type}>{type}</option>
            ))}
          </select>
        </div>
      </div>

      <div className="bg-white dark:bg-slate-800 rounded-xl shadow-sm border border-gray-100 dark:border-slate-700 overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead className="bg-gray-50 dark:bg-slate-700">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                  Tx Hash
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                  Type
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                  From
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                  To
                </th>
                <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                  Amount
                </th>
                <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                  Block
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100 dark:divide-slate-700">
              {isLoading ? (
                [...Array(10)].map((_, i) => (
                  <tr key={i} className="animate-pulse">
                    <td className="px-6 py-4"><div className="h-4 bg-gray-200 dark:bg-slate-700 rounded w-24" /></td>
                    <td className="px-6 py-4"><div className="h-4 bg-gray-200 dark:bg-slate-700 rounded w-16" /></td>
                    <td className="px-6 py-4"><div className="h-4 bg-gray-200 dark:bg-slate-700 rounded w-24" /></td>
                    <td className="px-6 py-4"><div className="h-4 bg-gray-200 dark:bg-slate-700 rounded w-24" /></td>
                    <td className="px-6 py-4"><div className="h-4 bg-gray-200 dark:bg-slate-700 rounded w-16 ml-auto" /></td>
                    <td className="px-6 py-4"><div className="h-4 bg-gray-200 dark:bg-slate-700 rounded w-12 ml-auto" /></td>
                  </tr>
                ))
              ) : data?.transactions?.length ? (
                data.transactions.map((tx) => (
                  <tr key={tx.hash} className="hover:bg-gray-50 dark:hover:bg-slate-700/50">
                    <td className="px-6 py-4 whitespace-nowrap">
                      <Link
                        href={`/transactions/${tx.hash}`}
                        className="text-primary-600 hover:text-primary-700 font-mono text-sm"
                      >
                        {truncateHash(tx.hash)}
                      </Link>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <span className={`px-2 py-1 rounded text-xs font-medium ${getTxTypeColor(tx.tx_type)}`}>
                        {tx.tx_type}
                      </span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <Link
                        href={`/accounts/${tx.from_address}`}
                        className="font-mono text-sm text-gray-600 dark:text-gray-300 hover:text-primary-600"
                      >
                        {truncateAddress(tx.from_address)}
                      </Link>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      {tx.to_address ? (
                        <Link
                          href={`/accounts/${tx.to_address}`}
                          className="font-mono text-sm text-gray-600 dark:text-gray-300 hover:text-primary-600"
                        >
                          {truncateAddress(tx.to_address)}
                        </Link>
                      ) : (
                        <span className="text-gray-400">-</span>
                      )}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-right text-sm text-gray-900 dark:text-white">
                      {formatCPC(tx.amount)} CPC
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-right">
                      <Link
                        href={`/blocks/${tx.block_height}`}
                        className="text-sm text-primary-600 hover:text-primary-700"
                      >
                        #{formatNumber(tx.block_height)}
                      </Link>
                    </td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td colSpan={6} className="px-6 py-8 text-center text-gray-500">
                    No transactions found
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>

        {/* Pagination */}
        {data?.pagination && data.pagination.pages > 1 && (
          <div className="flex items-center justify-between px-6 py-4 border-t border-gray-100 dark:border-slate-700">
            <div className="text-sm text-gray-500 dark:text-gray-400">
              Page {page} of {data.pagination.pages} ({formatNumber(data.pagination.total)} transactions)
            </div>
            <div className="flex space-x-2">
              <button
                onClick={() => setPage(page - 1)}
                disabled={page === 1}
                className="px-3 py-1 rounded border border-gray-300 dark:border-slate-600 disabled:opacity-50 disabled:cursor-not-allowed hover:bg-gray-100 dark:hover:bg-slate-700"
              >
                <ChevronLeft className="w-4 h-4" />
              </button>
              <button
                onClick={() => setPage(page + 1)}
                disabled={page >= data.pagination.pages}
                className="px-3 py-1 rounded border border-gray-300 dark:border-slate-600 disabled:opacity-50 disabled:cursor-not-allowed hover:bg-gray-100 dark:hover:bg-slate-700"
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
