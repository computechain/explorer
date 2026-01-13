'use client';

import { Blocks, ArrowLeftRight, Users, Zap } from 'lucide-react';
import { useQuery } from '@tanstack/react-query';
import { Stats, fetchTps } from '@/lib/api';
import { formatNumber, formatCPC } from '@/lib/utils';

interface StatsCardsProps {
  stats?: Stats;
  loading?: boolean;
}

export function StatsCards({ stats, loading }: StatsCardsProps) {
  const { data: tps } = useQuery({
    queryKey: ['tps'],
    queryFn: fetchTps,
    refetchInterval: 5000,
  });

  if (loading) {
    return (
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {[...Array(4)].map((_, i) => (
          <div
            key={i}
            className="bg-white dark:bg-slate-800 rounded-xl p-6 shadow-sm animate-pulse"
          >
            <div className="h-4 bg-gray-200 dark:bg-slate-700 rounded w-1/2 mb-4" />
            <div className="h-8 bg-gray-200 dark:bg-slate-700 rounded w-3/4" />
          </div>
        ))}
      </div>
    );
  }

  const cards = [
    {
      title: 'Block Height',
      value: formatNumber(stats?.blocks.latest_height || 0),
      icon: Blocks,
      color: 'text-blue-600',
      bgColor: 'bg-blue-100',
    },
    {
      title: 'Transactions',
      value: formatNumber(stats?.transactions.total || 0),
      icon: ArrowLeftRight,
      color: 'text-green-600',
      bgColor: 'bg-green-100',
    },
    {
      title: 'Accounts',
      value: formatNumber(stats?.accounts.total || 0),
      icon: Users,
      color: 'text-purple-600',
      bgColor: 'bg-purple-100',
    },
    {
      title: 'Current TPS',
      value: tps?.current_tps?.toFixed(1) || '0',
      subtitle: `Avg: ${tps?.avg_tps_1h?.toFixed(1) || '0'} TPS`,
      icon: Zap,
      color: 'text-orange-600',
      bgColor: 'bg-orange-100',
    },
  ];

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
      {cards.map((card) => (
        <div
          key={card.title}
          className="bg-white dark:bg-slate-800 rounded-xl p-6 shadow-sm border border-gray-100 dark:border-slate-700"
        >
          <div className="flex items-center justify-between mb-4">
            <span className="text-sm font-medium text-gray-500 dark:text-gray-400">
              {card.title}
            </span>
            <div className={`p-2 rounded-lg ${card.bgColor}`}>
              <card.icon className={`w-5 h-5 ${card.color}`} />
            </div>
          </div>
          <div className="text-2xl font-bold text-gray-900 dark:text-white">
            {card.value}
          </div>
          {card.subtitle && (
            <div className="text-sm text-gray-500 dark:text-gray-400 mt-1">
              {card.subtitle}
            </div>
          )}
        </div>
      ))}
    </div>
  );
}
