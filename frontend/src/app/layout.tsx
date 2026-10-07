import type { Metadata } from 'next';
import './globals.css';
import { Providers } from './providers';
import { Header } from '@/components/Header';
import { Footer } from '@/components/Footer';
import { ObserverStatus } from '@/components/ObserverStatus';


export const metadata: Metadata = {
  title: 'ComputeChain Explorer',
  description: 'Explore blocks, transactions, and accounts on ComputeChain',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className="font-sans">
        <Providers>
          <div className="min-h-screen flex flex-col">
            <Header />
            <ObserverStatus />
            <main className="flex-1 container mx-auto px-4 py-8">
              {children}
            </main>
            <Footer />
          </div>
        </Providers>
      </body>
    </html>
  );
}
