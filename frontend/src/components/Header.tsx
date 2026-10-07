'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { Blocks, ArrowLeftRight, Users, Search } from 'lucide-react';
import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { cn } from '@/lib/utils';
import { searchIndex } from '@/lib/api';

const navigation = [
  { name: 'Blocks', href: '/blocks', icon: Blocks },
  { name: 'Transactions', href: '/transactions', icon: ArrowLeftRight },
  { name: 'Accounts', href: '/accounts', icon: Users },
  { name: 'Validators', href: '/validators', icon: Users },
];

export function Header() {
  const pathname = usePathname();
  const router = useRouter();
  const [search, setSearch] = useState('');
  const [searchError, setSearchError] = useState('');

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!search.trim()) return;

    const query = search.trim();

    setSearchError('');
    try {
      const result = await searchIndex(query);
      router.push(result.path);
      setSearch('');
    } catch {
      setSearchError('Not found in the current index, or API unavailable.');
    }
  };

  return (
    <header className="bg-white dark:bg-slate-800 shadow-sm border-b border-gray-200 dark:border-slate-700">
      <div className="container mx-auto px-4">
        <div className="flex flex-wrap gap-3 items-center justify-between py-3">
          {/* Logo */}
          <Link href="/" className="flex items-center space-x-2">
            <div className="w-8 h-8 bg-primary-600 rounded-lg flex items-center justify-center">
              <span className="text-white font-bold text-lg">C</span>
            </div>
            <span className="font-bold text-xl text-gray-900 dark:text-white">
              ComputeChain Explorer
            </span>
          </Link>

          {/* Navigation */}
          <nav className="flex flex-wrap items-center gap-1" aria-label="Explorer">
            {navigation.map((item) => {
              const isActive = pathname.startsWith(item.href);
              return (
                <Link
                  key={item.name}
                  href={item.href}
                  className={cn(
                    'flex items-center px-3 py-2 rounded-lg text-sm font-medium transition-colors',
                    isActive
                      ? 'bg-primary-100 text-primary-700 dark:bg-primary-900 dark:text-primary-200'
                      : 'text-gray-600 hover:bg-gray-100 dark:text-gray-300 dark:hover:bg-slate-700'
                  )}
                >
                  <item.icon className="w-4 h-4 mr-2" />
                  {item.name}
                </Link>
              );
            })}
          </nav>

          {/* Search */}
          <form onSubmit={handleSearch} className="flex items-center">
            <div className="relative">
              <input
                type="text"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                placeholder="Search by address, tx hash, or block"
                maxLength={100}
                aria-label="Search chain index"
                className="w-64 pl-10 pr-4 py-2 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500 dark:bg-slate-700 dark:border-slate-600 dark:text-white"
              />
              <Search className="absolute left-3 top-2.5 w-4 h-4 text-gray-400" />
            </div>
            <button type="submit" className="ml-2 px-3 py-2 rounded bg-primary-600 text-white">Search</button>
          </form>
        </div>
        {searchError && <p role="alert" className="pb-3 text-sm text-red-600">{searchError}</p>}
      </div>
    </header>
  );
}
