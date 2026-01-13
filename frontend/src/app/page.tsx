'use client';

import { useQuery } from '@tanstack/react-query';
import { StatsCards } from '@/components/StatsCards';
import { RecentBlocks } from '@/components/RecentBlocks';
import { RecentTransactions } from '@/components/RecentTransactions';
import { fetchStats, fetchBlocks, fetchRecentTransactions } from '@/lib/api';

export default function Home() {
  const { data: stats, isLoading: statsLoading } = useQuery({
    queryKey: ['stats'],
    queryFn: fetchStats,
  });

  const { data: blocks, isLoading: blocksLoading } = useQuery({
    queryKey: ['blocks', 1],
    queryFn: () => fetchBlocks(1, 10),
  });

  const { data: transactions, isLoading: txLoading } = useQuery({
    queryKey: ['recent-transactions'],
    queryFn: () => fetchRecentTransactions(10),
  });

  return (
    <div className="space-y-8">
      {/* Stats Cards */}
      <StatsCards stats={stats} loading={statsLoading} />

      {/* Recent Activity */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        <RecentBlocks blocks={blocks?.blocks} loading={blocksLoading} />
        <RecentTransactions transactions={transactions?.transactions} loading={txLoading} />
      </div>
    </div>
  );
}
