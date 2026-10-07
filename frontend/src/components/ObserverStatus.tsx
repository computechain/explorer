'use client';
import { useQuery } from '@tanstack/react-query';
import { fetchStats } from '@/lib/api';

export function ObserverStatus() {
  const { data, error, isLoading } = useQuery({queryKey: ['stats'], queryFn: fetchStats});
  const online = data?.sync.online;
  return <section aria-live="polite" className={`px-4 py-3 text-sm border-b ${error || data && !online ? 'bg-amber-50 text-amber-900' : 'bg-indigo-50 text-indigo-900'}`}>
    <div className="container mx-auto">
      Local v3 devnet · read-only observer, not a wallet or independent light client.
      {isLoading ? ' Connecting…' : error ? ' API unavailable; live data cannot be verified.' : data ?
        ` Node ${data.sync.node_height}, indexed ${data.sync.indexed_height}, account state ${data.sync.state_height}. ${online ? '' : 'Node offline / stale data.'}` : ''}
      {data && online && data.sync.indexed_height < data.sync.node_height && ' History is catching up; totals are indexed history only.'}
    </div>
  </section>;
}
