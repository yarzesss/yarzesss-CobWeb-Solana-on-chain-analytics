'use client';

import { useState } from 'react';
import type { TokenAnalysis } from '@/lib/types';
import { Tabs } from '@/components/ui/Tabs';
import { DevRiskCard } from './DevRiskCard';
import { EarlyBuyersTable } from './EarlyBuyersTable';
import { CabalGraph2D } from './CabalGraph2D';
import { CabalGraph3D } from './CabalGraph3D';
import { ClusterCard } from './ClusterCard';
import { Card, CardTitle } from '@/components/ui/Card';
import { DevRiskBadge, Badge } from '@/components/ui/Badge';
import { AddressLink } from '@/components/shared/AddressLink';
import { getSolscanTokenUrl } from '@/lib/utils';

function compactNumber(n: number): string {
  if (n >= 1_000_000_000) return `${(n / 1_000_000_000).toFixed(2)}B`;
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(2)}M`;
  if (n >= 1_000) return `${(n / 1_000).toFixed(1)}K`;
  return n.toFixed(n < 1 ? 6 : 2);
}

export function TokenDashboard({
  data,
  analyzing = false,
}: {
  data: TokenAnalysis;
  analyzing?: boolean;
}) {
  const [tab, setTab] = useState('overview');
  const [graphMode, setGraphMode] = useState<'3d' | '2d'>('3d');

  const clusterCount = data.cabal.clusters.length;
  const independentCount = data.cabal.independent_wallets.length;

  const tabs = [
    { id: 'overview', label: 'Overview' },
    { id: 'buyers', label: 'Early Buyers', count: data.early_buyers_count },
    { id: 'cabal', label: 'Cabal Web', count: clusterCount },
    { id: 'dev', label: 'Dev Risk' },
  ];

  return (
    <div className="space-y-6">
      {data.lifecycle && !data.lifecycle.pending && data.lifecycle.stage !== 'unknown' && (
        <div className="flex flex-wrap items-center gap-3 font-mono text-xs">
          <span className="font-pixel text-[8px] uppercase text-gray-500">Lifecycle:</span>
          <span
            className={
              data.lifecycle.stage === 'markup'
                ? 'border border-cobweb-mint/60 bg-cobweb-mint/10 px-2 py-1 uppercase text-cobweb-mint'
                : data.lifecycle.stage === 'dump'
                  ? 'border border-cobweb-red/60 bg-cobweb-red/10 px-2 py-1 uppercase text-cobweb-red'
                  : 'border border-cobweb-amber/60 bg-cobweb-amber/10 px-2 py-1 uppercase text-cobweb-amber'
            }
          >
            {data.lifecycle.stage}
          </span>
          <span className="text-gray-500">
            last {data.lifecycle.window_trades} trades: {data.lifecycle.buy_count} buys /{' '}
            {data.lifecycle.sell_count} sells · {data.lifecycle.unique_buyers} buyers vs{' '}
            {data.lifecycle.unique_sellers} sellers
          </span>
          {data.buyers_source === 'index' && (
            <span className="border border-cobweb-cyan/60 px-2 py-1 text-cobweb-cyan">
              LIVE-INDEXED
            </span>
          )}
        </div>
      )}
      {analyzing && (
        <div className="flex items-center gap-3 border-2 border-cobweb-pink/40 bg-cobweb-pink/10 p-3">
          <span className="h-2 w-2 animate-pulse bg-cobweb-pink" />
          <p className="font-mono text-xs text-cobweb-pink-light">
            Deep analysis in progress: scanning wallet connections for cabal clusters…
            Buyers and entry data below are already final.
          </p>
        </div>
      )}
      {/* Token header */}
      <div className="pixel-card p-6">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
          <div>
            <div className="flex flex-wrap items-center gap-3 mb-2">
              <h1 className="font-pixel text-lg text-white">
                {data.name ?? 'Unknown Token'}
              </h1>
              {data.symbol && (
                <Badge variant="pink">${data.symbol}</Badge>
              )}
            </div>
            <AddressLink
              address={data.ca}
              externalHref={getSolscanTokenUrl(data.ca)}
              className="text-sm"
            />
          </div>

          <div className="flex flex-wrap gap-3">
            {data.market && !data.market.pending && data.market.source !== 'none' && (
              <>
                <div className="border-2 border-cobweb-border bg-cobweb-bg px-4 py-2 text-center">
                  <p className="font-pixel text-[8px] uppercase text-gray-500">Market Cap</p>
                  <p className="font-mono text-xl font-bold text-cobweb-mint">
                    {data.market.market_cap_usd != null
                      ? `$${compactNumber(data.market.market_cap_usd)}`
                      : '—'}
                  </p>
                  <p className="font-mono text-[9px] text-gray-600">
                    {data.market.venue === 'bonding_curve'
                      ? 'bonding curve · live trades'
                      : data.market.dex ?? ''}
                  </p>
                </div>
                {data.market.liquidity_usd != null && (
                  <div className="border-2 border-cobweb-border bg-cobweb-bg px-4 py-2 text-center">
                    <p className="font-pixel text-[8px] uppercase text-gray-500">Liquidity</p>
                    <p className="font-mono text-xl font-bold text-cobweb-cyan">
                      ${compactNumber(data.market.liquidity_usd)}
                    </p>
                  </div>
                )}
              </>
            )}
            {data.holders?.top10_pct != null && (
              <div className="border-2 border-cobweb-border bg-cobweb-bg px-4 py-2 text-center">
                <p className="font-pixel text-[8px] uppercase text-gray-500">Top 10 Hold</p>
                <p className={`font-mono text-xl font-bold ${
                  data.holders.top10_pct >= 50 ? 'text-cobweb-red'
                  : data.holders.top10_pct >= 30 ? 'text-cobweb-amber'
                  : 'text-cobweb-mint'
                }`}>
                  {data.holders.top10_pct}%
                </p>
              </div>
            )}
            <div className="border-2 border-cobweb-border bg-cobweb-bg px-4 py-2 text-center">
              <p className="font-pixel text-[8px] uppercase text-gray-500">Early Buyers</p>
              <p className="font-mono text-xl font-bold text-cobweb-pink-light">
                {data.early_buyers_count}
              </p>
            </div>
            <div className="border-2 border-cobweb-border bg-cobweb-bg px-4 py-2 text-center">
              <p className="font-pixel text-[8px] uppercase text-gray-500">Clusters</p>
              <p className="font-mono text-xl font-bold text-cobweb-amber">{clusterCount}</p>
            </div>
            <div className="border-2 border-cobweb-border bg-cobweb-bg px-4 py-2 text-center">
              <p className="font-pixel text-[8px] uppercase text-gray-500">Dev Risk</p>
              <DevRiskBadge level={data.dev_risk.level} />
            </div>
          </div>
        </div>
      </div>

      {data.early_buyers_count === 0 && (
        <div className="pixel-card p-6 text-center">
          <p className="font-pixel text-[10px] uppercase text-cobweb-amber mb-3">
            No early buyers detected
          </p>
          <p className="font-mono text-xs text-gray-400 max-w-xl mx-auto">
            Either this token has no purchase activity yet, or its launch is
            older than the analyzable history window. Cluster and buyer
            analysis below will be empty — that reflects the data, not a bug.
          </p>
        </div>
      )}

      <Tabs tabs={tabs} active={tab} onChange={setTab} />

      {tab === 'overview' && (
        <div className="grid gap-6 lg:grid-cols-2">
          <DevRiskCard devRisk={data.dev_risk} />
          <Card>
            <CardTitle className="mb-4">Cabal Summary</CardTitle>
            {clusterCount === 0 ? (
              <div className="border-2 border-dashed border-cobweb-mint/40 bg-cobweb-mint/5 p-6 text-center">
                <p className="font-pixel text-[10px] uppercase text-cobweb-mint mb-2">
                  No Coordinated Clusters
                </p>
                <p className="font-mono text-xs text-gray-400">
                  {independentCount} independent early buyers detected — likely organic Smart Money.
                </p>
              </div>
            ) : (
              <div className="space-y-2 font-mono text-sm text-gray-300">
                <p>
                  <span className="text-cobweb-red font-bold">{clusterCount}</span> suspicious
                  cluster{clusterCount !== 1 ? 's' : ''} found
                </p>
                <p>
                  <span className="text-cobweb-mint font-bold">{independentCount}</span> wallets
                  appear independent
                </p>
              </div>
            )}
          </Card>
          {data.cabal.clusters.slice(0, 2).map((c, i) => (
            <ClusterCard key={i} cluster={c} index={i} />
          ))}
        </div>
      )}

      {tab === 'buyers' && (
        <Card>
          <EarlyBuyersTable buyers={data.early_buyers} currentMcapUsd={data.market?.market_cap_usd} />
        </Card>
      )}

      {tab === 'buyers' && (
        <Card>
          <EarlyBuyersTable buyers={data.early_buyers} currentMcapUsd={data.market?.market_cap_usd} />
        </Card>
      )}

      {tab === 'cabal' && (
        <div className="space-y-6">
          <div className="flex gap-2">
            <button
              type="button"
              onClick={() => setGraphMode('3d')}
              className={graphMode === '3d' ? 'pixel-tab-active' : 'pixel-tab'}
            >
              3D Web
            </button>
            <button
              type="button"
              onClick={() => setGraphMode('2d')}
              className={graphMode === '2d' ? 'pixel-tab-active' : 'pixel-tab'}
            >
              2D Pixel Map
            </button>
          </div>

          <Card className="p-2 sm:p-4">
            {graphMode === '3d' ? (
              <CabalGraph3D cabal={data.cabal} />
            ) : (
              <CabalGraph2D cabal={data.cabal} />
            )}
          </Card>

          <div className="grid gap-4 md:grid-cols-2">
            {data.cabal.clusters.map((c, i) => (
              <ClusterCard key={i} cluster={c} index={i} />
            ))}
          </div>

          {independentCount > 0 && (
            <Card>
              <CardTitle className="mb-3">Independent Wallets</CardTitle>
              <div className="flex flex-wrap gap-3">
                {data.cabal.independent_wallets.map((w) => (
                  <AddressLink key={w} address={w} href={`/wallet/${w}`} />
                ))}
              </div>
            </Card>
          )}
        </div>
      )}

      {tab === 'dev' && (
        <div className="max-w-xl">
          <DevRiskCard devRisk={data.dev_risk} />
        </div>
      )}
    </div>
  );
}
