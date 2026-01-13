'use client';

import { useState } from 'react';
import Link from 'next/link';
import { useQuery } from '@tanstack/react-query';
import { Users, ChevronLeft, ChevronRight, ArrowUpDown } from 'lucide-react';
import { fetchAccounts } from '@/lib/api';
import { formatNumber, truncateAddress, formatCPC } from '@/lib/utils';

export default function AccountsPage() {
  const [page, setPage] = useState(1);
  const [sortBy, setSortBy] = useState('balance');
  const [order, setOrder] = useState('desc');
  const limit = 25;

  const { data, isLoading } = useQuery({
    queryKey: ['accounts', page, sortBy, order],
    queryFn: () => fetchAccounts(page, limit, sortBy, order),
  });

  const toggleSort = (field: string) => {
    if (sortBy === field) {
      setOrder(order === 'desc' ? 'asc' : 'desc');
    } else {
      setSortBy(field);
      setOrder('desc');
    }
    setPage(1);
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center">
        <Users className="w-8 h-8 text-primary-600 mr-3" />
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Accounts</h1>
      </div>

      <div className="bg-white dark:bg-slate-800 rounded-xl shadow-sm border border-gray-100 dark:border-slate-700 overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead className="bg-gray-50 dark:bg-slate-700">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                  #
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                  Address
                </th>
                <th
                  className="px-6 py-3 text-right text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider cursor-pointer hover:text-gray-700"
                  onClick={() => toggleSort('balance')}
                >
                  <span className="flex items-center justify-end">
                    Balance
                    <ArrowUpDown className="w-3 h-3 ml-1" />
                  </span>
                </th>
                <th
                  className="px-6 py-3 text-right text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider cursor-pointer hover:text-gray-700"
                  onClick={() => toggleSort('tx_count')}
                >
                  <span className="flex items-center justify-end">
                    Txs
                    <ArrowUpDown className="w-3 h-3 ml-1" />
                  </span>
                </th>
                <th className="px-6 py-3 text-center text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                  Type
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100 dark:divide-slate-700">
              {isLoading ? (
                [...Array(10)].map((_, i) => (
                  <tr key={i} className="animate-pulse">
                    <td className="px-6 py-4"><div className="h-4 bg-gray-200 dark:bg-slate-700 rounded w-8" /></td>
                    <td className="px-6 py-4"><div className="h-4 bg-gray-200 dark:bg-slate-700 rounded w-40" /></td>
                    <td className="px-6 py-4"><div className="h-4 bg-gray-200 dark:bg-slate-700 rounded w-24 ml-auto" /></td>
                    <td className="px-6 py-4"><div className="h-4 bg-gray-200 dark:bg-slate-700 rounded w-12 ml-auto" /></td>
                    <td className="px-6 py-4"><div className="h-4 bg-gray-200 dark:bg-slate-700 rounded w-16 mx-auto" /></td>
                  </tr>
                ))
              ) : data?.accounts?.length ? (
                data.accounts.map((account, idx) => (
                  <tr key={account.address} className="hover:bg-gray-50 dark:hover:bg-slate-700/50">
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      {(page - 1) * limit + idx + 1}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <Link
                        href={`/accounts/${account.address}`}
                        className="text-primary-600 hover:text-primary-700 font-mono text-sm"
                      >
                        {truncateAddress(account.address, 12)}
                      </Link>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-right text-sm text-gray-900 dark:text-white">
                      {formatCPC(account.balance)} CPC
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-right text-sm text-gray-500 dark:text-gray-400">
                      {formatNumber(account.tx_count)}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-center">
                      {account.is_validator ? (
                        <span className="px-2 py-1 rounded text-xs font-medium bg-purple-100 text-purple-800">
                          Validator
                        </span>
                      ) : (
                        <span className="px-2 py-1 rounded text-xs font-medium bg-gray-100 text-gray-800">
                          Account
                        </span>
                      )}
                    </td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td colSpan={5} className="px-6 py-8 text-center text-gray-500">
                    No accounts found
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
              Page {page} of {data.pagination.pages} ({formatNumber(data.pagination.total)} accounts)
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
