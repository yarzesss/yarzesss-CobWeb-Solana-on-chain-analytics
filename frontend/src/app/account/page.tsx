'use client';

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '@/lib/api';
import { useAuth } from '@/lib/auth-context';
import { AuthForm } from '@/components/auth/AuthForm';
import { LoadingSpinner } from '@/components/ui/Loading';
import { Button } from '@/components/ui/Button';
import { Coby } from '@/components/mascot/Coby';
import Link from 'next/link';

function money(v: number) {
  return `$${v.toLocaleString(undefined, { maximumFractionDigits: 2 })}`;
}
function pnlColor(v: number) {
  return v >= 0 ? 'text-cobweb-mint' : 'text-cobweb-red';
}

export default function AccountPage() {
  const { nickname, loading, logout } = useAuth();
  const qc = useQueryClient();
  const [sizeInput, setSizeInput] = useState('');

  const account = useQuery({
    queryKey: ['account'],
    queryFn: () => api.getAccount(),
    enabled: !!nickname,
    refetchInterval: 20_000,
  });

  const sizeMutation = useMutation({
    mutationFn: (size: number) => api.setPositionSize(size),
    onSuccess: () => {
      setSizeInput('');
      qc.invalidateQueries({ queryKey: ['account'] });
    },
  });

  const resetMutation = useMutation({
    mutationFn: () => api.resetAccount(),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['account'] }),
  });

  if (loading) {
    return (
      <div className="mx-auto max-w-md px-4 py-16">
        <LoadingSpinner label="Loading..." />
      </div>
    );
  }

  // Logged out → show auth
  if (!nickname) {
    return (
      <div className="mx-auto max-w-md px-4 py-16">
        <div className="mb-8 flex flex-col items-center text-center">
          <Coby size={80} />
          <h1 className="mt-4 font-pixel text-sm uppercase text-cobweb-pink-light">
            Join the Competition
          </h1>
          <p className="mt-2 font-mono text-xs text-cobweb-muted">
            Create an account, get a $1,000 demo balance, follow real wallets, and
            see if their trades would have made you money.
          </p>
        </div>
        <AuthForm />
      </div>
    );
  }

  const a = account.data;

  return (
    <div className="mx-auto max-w-4xl px-4 py-8">
      <div className="mb-6 flex items-center justify-between">
        <div>
          <span className="eyebrow">Your Account</span>
          <h1 className="mt-1 font-pixel text-sm text-white">{nickname}</h1>
        </div>
        <Button size="sm" variant="ghost" onClick={logout}>
          Log out
        </Button>
      </div>

      {account.isLoading && <LoadingSpinner label="Loading account..." />}

      {a && (
        <div className="space-y-6">
          {/* Equity hero */}
          <div className="pixel-card-accent p-6">
            <span className="eyebrow">Total Equity</span>
            <div className="mt-1 flex flex-wrap items-baseline gap-3">
              <span className="font-pixel text-3xl text-white">{money(a.equity_usd)}</span>
              <span className={`font-mono text-sm ${pnlColor(a.total_pnl_usd)}`}>
                {a.total_pnl_usd >= 0 ? '+' : ''}{money(a.total_pnl_usd)} (
                {a.total_pnl_pct >= 0 ? '+' : ''}{a.total_pnl_pct}%)
              </span>
            </div>
            <div className="mt-4 grid grid-cols-2 gap-3 sm:grid-cols-4">
              <div className="stat-cell">
                <p className="text-[10px] text-cobweb-muted">Cash</p>
                <p className="font-mono text-sm text-gray-200">{money(a.balance_usd)}</p>
              </div>
              <div className="stat-cell">
                <p className="text-[10px] text-cobweb-muted">In Positions</p>
                <p className="font-mono text-sm text-gray-200">{money(a.open_value_usd)}</p>
              </div>
              <div className="stat-cell">
                <p className="text-[10px] text-cobweb-muted">Realized P&amp;L</p>
                <p className={`font-mono text-sm ${pnlColor(a.realized_pnl_usd)}`}>
                  {money(a.realized_pnl_usd)}
                </p>
              </div>
              <div className="stat-cell">
                <p className="text-[10px] text-cobweb-muted">Winrate</p>
                <p className="font-mono text-sm text-gray-200">
                  {a.closed_trades > 0 ? `${(a.winrate * 100).toFixed(0)}%` : '—'}
                  <span className="ml-1 text-[10px] text-gray-600">({a.closed_trades})</span>
                </p>
              </div>
            </div>
          </div>

          {/* Settings */}
          <div className="pixel-card p-5">
            <span className="eyebrow">Settings</span>
            <div className="mt-3 flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
              <div className="flex-1">
                <label className="mb-1 block font-mono text-xs text-cobweb-muted">
                  Position size per copied trade
                </label>
                <div className="flex gap-2">
                  <input
                    type="number"
                    value={sizeInput}
                    onChange={(e) => setSizeInput(e.target.value)}
                    placeholder={`${a.position_size_usd}`}
                    className="w-32 border-2 border-cobweb-border bg-cobweb-bg px-3 py-2 font-mono text-xs text-gray-200 outline-none focus:border-cobweb-pink"
                  />
                  <Button
                    size="sm"
                    onClick={() => {
                      const v = parseFloat(sizeInput);
                      if (!Number.isNaN(v) && v > 0) sizeMutation.mutate(v);
                    }}
                    disabled={sizeMutation.isPending}
                  >
                    Save
                  </Button>
                </div>
                <p className="mt-1 font-mono text-[10px] text-gray-600">
                  Currently {money(a.position_size_usd)}. Each time a followed wallet buys,
                  this much demo cash enters the trade.
                </p>
              </div>
              <Button
                size="sm"
                variant="ghost"
                onClick={() => {
                  if (confirm('Reset balance to $1,000 and clear all positions?')) {
                    resetMutation.mutate();
                  }
                }}
                disabled={resetMutation.isPending}
              >
                Reset to $1,000
              </Button>
            </div>
          </div>

          {/* Open positions */}
          <div className="pixel-card p-5">
            <div className="mb-3 flex items-center justify-between">
              <span className="eyebrow">Open Positions ({a.open_positions.length})</span>
              <Link href="/watchlist" className="font-mono text-[10px] text-cobweb-cyan hover:underline">
                Manage followed wallets →
              </Link>
            </div>
            {a.open_positions.length === 0 ? (
              <p className="py-4 font-mono text-xs text-cobweb-muted">
                No open positions yet. Follow wallets on your{' '}
                <Link href="/watchlist" className="text-cobweb-cyan hover:underline">
                  watchlist
                </Link>
                . When they buy a token, the bot opens a virtual position here.
              </p>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full min-w-[520px] font-mono text-xs">
                  <thead>
                    <tr className="border-b border-cobweb-border text-left text-cobweb-muted">
                      <th className="py-2">Token</th>
                      <th className="py-2 text-right">Invested</th>
                      <th className="py-2 text-right">Now</th>
                      <th className="py-2 text-right">P&amp;L</th>
                    </tr>
                  </thead>
                  <tbody>
                    {a.open_positions.map((p) => (
                      <tr key={p.mint} className="border-b border-cobweb-border/30">
                        <td className="py-2">
                          <Link href={`/token/${p.mint}`} className="text-cobweb-cyan hover:underline">
                            {p.mint.slice(0, 6)}…{p.mint.slice(-4)}
                          </Link>
                        </td>
                        <td className="py-2 text-right text-gray-300">{money(p.invested_usd)}</td>
                        <td className="py-2 text-right text-gray-300">
                          {p.priced ? money(p.current_value_usd) : <span className="text-gray-600">unpriced</span>}
                        </td>
                        <td className={`py-2 text-right ${pnlColor(p.unrealized_pnl_usd)}`}>
                          {p.unrealized_pnl_usd >= 0 ? '+' : ''}{money(p.unrealized_pnl_usd)}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>

          <p className="font-mono text-[10px] text-gray-600">
            This is a paper-trading simulation. Balances are virtual. Not financial advice.
            Copy-trades fire in real time once the Helius webhook is connected.
          </p>
        </div>
      )}
    </div>
  );
}
