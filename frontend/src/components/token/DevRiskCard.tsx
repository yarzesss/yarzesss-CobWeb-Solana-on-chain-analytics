import type { DevRisk } from '@/lib/types';
import { Card, CardHeader, CardTitle } from '@/components/ui/Card';
import { DevRiskBadge } from '@/components/ui/Badge';
import { ScoreBar } from '@/components/shared/ScoreBar';
import { AddressLink } from '@/components/shared/AddressLink';
import { getSolscanWalletUrl } from '@/lib/utils';

export function DevRiskCard({ devRisk }: { devRisk: DevRisk }) {
  const noDeployer = !devRisk.dev_wallet;

  return (
    <Card>
      <CardHeader>
        <CardTitle>Dev Risk Analysis</CardTitle>
        {!noDeployer && <DevRiskBadge level={devRisk.level} />}
      </CardHeader>

      {noDeployer ? (
        // Honest empty state — the old card silently showed zeros here,
        // which read as "nothing works". Now we say why.
        <div className="border-2 border-cobweb-border-soft bg-cobweb-bg-soft p-4">
          <p className="font-mono text-xs leading-relaxed text-cobweb-muted">
            Couldn&apos;t resolve a deployer wallet for this token from its on-chain
            metadata, so dev-history analysis isn&apos;t available. This is common for
            tokens whose mint authority is a program (e.g. pump.fun) rather than an
            individual wallet.
          </p>
        </div>
      ) : (
        <>
          <ScoreBar score={devRisk.score} label="Risk Score" className="mb-4" />

          <dl className="grid grid-cols-2 gap-3 font-mono text-xs">
            <div className="stat-cell">
              <dt className="mb-1 text-cobweb-muted">Previous Tokens</dt>
              <dd className="text-lg font-bold text-gray-100">
                {devRisk.dev_prev_tokens ?? 0}
              </dd>
            </div>
            <div className="stat-cell">
              <dt className="mb-1 text-cobweb-muted">Quick Sell Signal</dt>
              <dd className={devRisk.quick_sell_signal ? 'font-bold text-cobweb-red' : 'text-cobweb-mint'}>
                {devRisk.quick_sell_signal ? 'DETECTED' : 'None'}
              </dd>
            </div>
          </dl>

          <div className="mt-4 border-t-2 border-cobweb-border-soft pt-3">
            <p className="eyebrow mb-2">Deployer Wallet</p>
            <AddressLink
              address={devRisk.dev_wallet!}
              href={`/wallet/${devRisk.dev_wallet}`}
              externalHref={getSolscanWalletUrl(devRisk.dev_wallet!)}
            />
          </div>
        </>
      )}
    </Card>
  );
}
