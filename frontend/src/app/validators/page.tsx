'use client';
import Link from 'next/link';
import { useQuery } from '@tanstack/react-query';
import { fetchValidators } from '@/lib/api';
import { formatCPC, formatNumber } from '@/lib/utils';

export default function Validators() {
  const {data, isLoading, error} = useQuery({queryKey:['validators'],queryFn:fetchValidators});
  return <div className="space-y-5">
    <h1 className="text-2xl font-bold">Validators</h1>
    <p className="text-sm text-gray-500">Consensus keys and CPC owners are separate identities. Native power is at the observed height; scheduled power includes changes effective at H+2. No protocol rewards are enabled.</p>
    {isLoading && <p>Loading validators…</p>}
    {error && <p role="alert">Validator API unavailable.</p>}
    {data && <><p>Application state: height {data.state_height}</p>
      <div className="grid gap-4 md:grid-cols-2">{data.validators.map(val => <article key={val.pub_key} className="p-5 rounded-xl border bg-white dark:bg-slate-800 dark:border-slate-700 space-y-3">
        <h2 className="font-semibold">{val.tombstoned ? 'Tombstoned' : BigInt(val.native_power) > 0n ? 'Voting' : 'Not voting'} · power {formatNumber(val.native_power)}</h2>
        <p className="text-xs font-mono break-all">Ed25519 {val.pub_key}</p>
        <p className="text-sm break-all">Owner: <Link className="text-primary-600 font-mono" href={`/accounts/${val.owner}`}>{val.owner}</Link></p>
        <dl className="grid grid-cols-2 gap-2 text-sm">
          <dt>Self stake</dt><dd>{formatCPC(val.self_stake)} CPC</dd>
          <dt>Delegated</dt><dd>{formatCPC(val.delegated)} CPC</dd>
          <dt>Scheduled power</dt><dd>{formatNumber(val.scheduled_power)}</dd>
          <dt>Commission</dt><dd>{(val.commission_bps/100).toFixed(2)}% (no payouts yet)</dd>
          <dt>Burned penalty</dt><dd>{formatCPC(val.penalties)} CPC</dd>
        </dl>
        {val.commission_change && <p className="text-sm">Scheduled commission {(val.commission_change.bps/100).toFixed(2)}% at H{val.commission_change.height}</p>}
      </article>)}</div>
    </>}
  </div>;
}
