'use client';

import Link from 'next/link';
import { Blocks, ArrowRight } from 'lucide-react';
import { Block } from '@/lib/api';
import { truncateAddress, formatTimeAgo, formatNumber } from '@/lib/utils';

interface RecentBlocksProps {
  blocks?: Block[];
  loading?: boolean;
}

export function RecentBlocks({ blocks, loading }: RecentBlocksProps) {
  return (
    <div className="bg-white dark:bg-slate-800 rounded-xl shadow-sm border border-gray-100 dark:border-slate-700">
      <div className="flex items-center justify-between p-4 border-b border-gray-100 dark:border-slate-700">
        <div className="flex items-center">
          <Blocks className="w-5 h-5 text-primary-600 mr-2" />
          <h2 className="text-lg font-semibold text-gray-900 dark:text-white">
            Recent Blocks
          </h2>
        </div>
        <Link
          href="/blocks"
          className="text-sm text-primary-600 hover:text-primary-700 flex items-center"
        >
          View all <ArrowRight className="w-4 h-4 ml-1" />
        </Link>
      </div>

      <div className="divide-y divide-gray-100 dark:divide-slate-700">
        {loading ? (
          [...Array(5)].map((_, i) => (
            <div key={i} className="p-4 animate-pulse">
              <div className="h-4 bg-gray-200 dark:bg-slate-700 rounded w-1/4 mb-2" />
              <div className="h-3 bg-gray-200 dark:bg-slate-700 rounded w-1/2" />
            </div>
          ))
        ) : blocks?.length ? (
          blocks.map((block) => (
            <div key={block.height} className="p-4 hover:bg-gray-50 dark:hover:bg-slate-700/50">
              <div className="flex items-center justify-between">
                <div>
                  <Link
                    href={`/blocks/${block.height}`}
                    className="text-primary-600 hover:text-primary-700 font-medium"
                  >
                    #{formatNumber(block.height)}
                  </Link>
                  <div className="text-sm text-gray-500 dark:text-gray-400 mt-1">
                    <span className="font-mono">{truncateAddress(block.proposer)}</span>
                  </div>
                </div>
                <div className="text-right">
                  <div className="text-sm text-gray-900 dark:text-white">
                    {block.tx_count} txs
                  </div>
                  <div className="text-xs text-gray-500 dark:text-gray-400">
                    {formatTimeAgo(block.timestamp)}
                  </div>
                </div>
              </div>
            </div>
          ))
        ) : (
          <div className="p-8 text-center text-gray-500">No blocks found</div>
        )}
      </div>
    </div>
  );
}
