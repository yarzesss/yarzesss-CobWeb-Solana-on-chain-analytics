'use client';

import { useQuery } from '@tanstack/react-query';
import Link from 'next/link';
import { api } from '@/lib/api';
import { useAuth } from '@/lib/auth-context';
import { LoadingSpinner } from '@/components/ui/Loading';

function pnlColor(v: number) {
  return v >= 0 ? 'text-cobweb-mint' : 'text-cobweb-red';
}

export default function LeaderboardPage() {
  const { nickname } = useAuth();
  const { data, isLoading, error } = useQuery({
    queryKey: ['leaderboard'],
    queryFn: () => api.getLeaderboard(),
    refetchInterval: 30_000,
  });

  return (
    <div className="mx-auto max-w-4xl px-4 py-8">
      <span className="eyebrow">The Competition</span>
      <h1 className="mt-2 font-pixel text-sm uppercase text-cobweb-pink-light">
        Trader Leaderboard
      </h1>
      <p className="mb-6 mt-2 font-mono text-xs text-cobweb-muted">
        Players ranked by demo equity — cash plus open positions. Who picked the
        best wallets to copy?
      </p>

      {isLoading && <LoadingSpinner label="Loading rankings..." />}

      {error != null && (
        <div className="pixel-card p-6 font-mono text-sm text-cobweb-red">
          Couldn&apos;t load the leaderboard. Is the backend running?
        </div>
      )}

      {data && data.entries.length === 0 && (
        <div className="pixel-card p-8 text-center">
          <p className="mb-3 font-pixel text-[10px] uppercase text-cobweb-amber">
            No players yet
          </p>
          <p className="mx-auto max-w-md font-mono text-xs text-cobweb-muted">
            {data.message ?? 'Be the first — create an account, follow some wallets, and climb.'}
          </p>
          {!nickname && (
            <Link href="/account" className="mt-4 inline-block pixel-btn">
              Get Started
            </Link>
          )}
        </div>
      )}

      {data && data.entries.length > 0 && (
        <div className="overflow-x-auto border-2 border-cobweb-border">
          <table className="w-full min-w-[560px] font-mono text-xs">
            <thead>
              <tr className="border-b-2 border-cobweb-border bg-cobweb-surface2 text-left font-pixel text-[8px] uppercase text-gray-400">
                <th className="px-3 py-2">#</th>
                <th className="px-3 py-2">Player</th>
                <th className="px-3 py-2">Equity</th>
                <th className="px-3 py-2">P&amp;L</th>
                <th className="px-3 py-2">Trades</th>
                <th className="px-3 py-2">Winrate</th>
              </tr>
            </thead>
            <tbody>
              {data.entries.map((e) => {
                const isMe = e.nickname === nickname;
                return (
                  <tr
                    key={e.nickname}
                    className={`border-b border-cobweb-border/50 transition-colors hover:bg-cobweb-surface2/50 ${
                      isMe ? 'bg-cobweb-pink/10' : ''
                    }`}
                  >
                    <td className="px-3 py-2 text-cobweb-pink">{e.rank}</td>
                    <td className="px-3 py-2 font-bold text-gray-200">
                      {e.nickname}
                      {isMe && <span className="ml-2 text-[9px] text-cobweb-pink-light">you</span>}
                    </td>
                    <td className="px-3 py-2 text-gray-200">${e.equity_usd.toLocaleString()}</td>
                    <td className={`px-3 py-2 ${pnlColor(e.total_pnl_usd)}`}>
                      {e.total_pnl_usd >= 0 ? '+' : ''}${e.total_pnl_usd.toLocaleString()}
                      <span className="ml-1 text-[10px] opacity-70">
                        ({e.total_pnl_pct >= 0 ? '+' : ''}{e.total_pnl_pct}%)
                      </span>
                    </td>
                    <td className="px-3 py-2 text-gray-400">{e.closed_trades}</td>
                    <td className="px-3 py-2 text-gray-400">
                      {e.closed_trades > 0 ? `${(e.winrate * 100).toFixed(0)}%` : '—'}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
