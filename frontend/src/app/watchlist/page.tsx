'use client';

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import Link from 'next/link';
import { api } from '@/lib/api';
import { useAuth } from '@/lib/auth-context';
import { AddressLink } from '@/components/shared/AddressLink';
import { Button } from '@/components/ui/Button';
import { LoadingSpinner } from '@/components/ui/Loading';
import { AuthForm } from '@/components/auth/AuthForm';
import { Coby } from '@/components/mascot/Coby';
import { getSolscanWalletUrl } from '@/lib/utils';

const SOLANA_RE = /^[1-9A-HJ-NP-Za-km-z]{32,44}$/;

export default function WatchlistPage() {
  const { nickname, loading } = useAuth();
  const qc = useQueryClient();
  const [address, setAddress] = useState('');
  const [label, setLabel] = useState('');
  const [error, setError] = useState<string | null>(null);

  const list = useQuery({
    queryKey: ['watchlist'],
    queryFn: () => api.getWatchlist(),
    enabled: !!nickname,
  });

  const addMutation = useMutation({
    mutationFn: ({ w, l }: { w: string; l?: string }) => api.addWatch(w, l),
    onSuccess: () => {
      setAddress('');
      setLabel('');
      qc.invalidateQueries({ queryKey: ['watchlist'] });
    },
    onError: (e) => {
      const msg = e instanceof Error ? e.message : '';
      setError(msg.includes('Already') ? 'Already following this wallet.' : 'Could not add wallet.');
    },
  });

  const removeMutation = useMutation({
    mutationFn: (w: string) => api.removeWatch(w),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['watchlist'] }),
  });

  const add = () => {
    setError(null);
    const addr = address.trim();
    if (!SOLANA_RE.test(addr)) return setError('That does not look like a Solana address.');
    addMutation.mutate({ w: addr, l: label.trim() || undefined });
  };

  if (loading) {
    return <div className="mx-auto max-w-md px-4 py-16"><LoadingSpinner /></div>;
  }

  if (!nickname) {
    return (
      <div className="mx-auto max-w-md px-4 py-16">
        <div className="mb-8 flex flex-col items-center text-center">
          <Coby size={72} />
          <h1 className="mt-4 font-pixel text-sm uppercase text-cobweb-pink-light">
            Sign in to follow wallets
          </h1>
          <p className="mt-2 font-mono text-xs text-cobweb-muted">
            Your watchlist drives the copy-trade bot. Create an account to start.
          </p>
        </div>
        <AuthForm />
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-4xl px-4 py-8">
      <span className="eyebrow">Copy-Trade Watchlist</span>
      <h1 className="mt-2 font-pixel text-sm text-cobweb-pink-light">Followed Wallets</h1>
      <p className="mb-6 mt-2 font-mono text-xs text-cobweb-muted">
        When any of these wallets buys a token, the bot opens a virtual position on your
        demo balance. When they sell, it closes. Tune your position size on the{' '}
        <Link href="/account" className="text-cobweb-cyan hover:underline">account page</Link>.
      </p>

      <div className="mb-6 border-2 border-cobweb-border bg-cobweb-surface p-4">
        <p className="mb-3 font-pixel text-[9px] uppercase text-gray-300">Follow a Wallet</p>
        <div className="flex flex-col gap-2 sm:flex-row">
          <input
            value={address}
            onChange={(e) => setAddress(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && add()}
            placeholder="Wallet address"
            className="flex-1 border-2 border-cobweb-border bg-cobweb-bg px-3 py-2 font-mono text-xs text-gray-200 outline-none focus:border-cobweb-pink"
          />
          <input
            value={label}
            onChange={(e) => setLabel(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && add()}
            placeholder="Label (optional)"
            className="w-full border-2 border-cobweb-border bg-cobweb-bg px-3 py-2 font-mono text-xs text-gray-200 outline-none focus:border-cobweb-pink sm:w-44"
          />
          <Button onClick={add} disabled={addMutation.isPending}>Follow</Button>
        </div>
        {error && <p className="mt-2 font-mono text-xs text-cobweb-amber">{error}</p>}
      </div>

      {list.isLoading && <LoadingSpinner label="Loading watchlist..." />}

      {list.data && list.data.length === 0 && (
        <div className="pixel-card p-8 text-center">
          <p className="font-mono text-xs text-cobweb-muted">
            No wallets followed yet. Add one above, or open any wallet from a token
            analysis and hit &quot;Copy this wallet&quot;.
          </p>
        </div>
      )}

      {list.data && list.data.length > 0 && (
        <div className="overflow-x-auto border-2 border-cobweb-border">
          <table className="w-full min-w-[480px] font-mono text-xs">
            <thead>
              <tr className="border-b-2 border-cobweb-border bg-cobweb-surface2 text-left font-pixel text-[8px] uppercase text-gray-400">
                <th className="px-3 py-2">Wallet</th>
                <th className="px-3 py-2">Label</th>
                <th className="px-3 py-2" />
              </tr>
            </thead>
            <tbody>
              {list.data.map((item) => (
                <tr key={item.wallet} className="border-b border-cobweb-border/50 hover:bg-cobweb-surface2/50">
                  <td className="px-3 py-2">
                    <AddressLink
                      address={item.wallet}
                      href={`/wallet/${item.wallet}`}
                      externalHref={getSolscanWalletUrl(item.wallet)}
                    />
                  </td>
                  <td className="px-3 py-2 text-gray-300">{item.label ?? '—'}</td>
                  <td className="px-3 py-2 text-right">
                    <button
                      type="button"
                      onClick={() => removeMutation.mutate(item.wallet)}
                      className="font-pixel text-[8px] uppercase text-cobweb-red hover:text-red-400"
                    >
                      Unfollow
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
