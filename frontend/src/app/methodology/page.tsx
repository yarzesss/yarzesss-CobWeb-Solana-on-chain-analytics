export const metadata = { title: 'Methodology — CobWeb' };

const SECTIONS = [
  {
    title: 'Early Buyers',
    body: 'A wallet counts as an early buyer only if it received the token AND spent SOL in the same transaction — this filters out airdrops, LP seeding and DEX vault legs. For tokens covered by our real-time index, the order and launch slot are exact; otherwise they are reconstructed from up to 3,000 transactions of history (oldest-first).',
  },
  {
    title: 'Bot Score',
    body: 'Based on how many blocks after launch the wallet bought: under 3 blocks scores 85 (near-certain automation), under 10 scores 65, under 30 scores 35, later entries score 12. Buying within seconds of a launch is mechanically impossible for a human reading a ticker.',
  },
  {
    title: 'Smart Money Score',
    body: 'Starts at 20. Organic timing (30+ blocks after launch) adds 15. Conviction adds up to 30: a position at least 2x the median of fellow early buyers signals independent research, not noise. Independence from any detected cluster adds 10. Wallets flagged as bots score 0; members of suspicious clusters cap at 15 — coordinated buying is not "smart", it is inside knowledge. The Smart Money tab shows wallets scoring 55+.',
  },
  {
    title: 'Cabal Clusters',
    body: 'Three connection layers: temporal (3+ wallets buying within the same 60-second window), common funder (wallets whose first SOL came from the same address — known exchange hot wallets like Binance or Bybit are excluded, since a shared CEX is not a shared owner), and direct transfers between early buyers. Suspicion score grows with cluster size and connection density.',
  },
  {
    title: 'Dev Risk',
    body: 'The deployer wallet is profiled for prior token launches and quick-sell behavior. A deployer with a history of launching and dumping scores HIGH regardless of how the current token looks.',
  },
  {
    title: 'Lifecycle Stage',
    body: 'From the latest ~100 transactions: buy ratio ≥62% reads as markup, ≤38% as dump; the balanced middle is accumulation when unique buyers outnumber sellers and distribution otherwise. Fewer than 5 classified trades returns unknown — we do not manufacture a verdict from noise.',
  },
  {
    title: 'Market Data',
    body: 'Listed tokens are priced via DexScreener. Fresh bonding-curve launches not on any DEX get a volume-weighted price derived from their actual recent on-chain trades, with outliers beyond 4x of the median trimmed (MEV, dust). If nothing trades, we show a dash — never an invented number.',
  },
  {
    title: 'PnL & Copy-Trade Simulator',
    body: 'Realized PnL is computed from actual SOL flows across the last 500 transactions, parsing both standard swap events and raw pump.fun transfers. Unrealized PnL prices open positions via DexScreener; positions without a price are reported as unpriced rather than counted as zero. The simulator replays trades within the chosen window and reports realized ROI — no slippage modeling, open positions excluded. None of this is financial advice.',
  },
];

export default function MethodologyPage() {
  return (
    <div className="mx-auto max-w-3xl px-4 py-8">
      <h1 className="font-pixel text-sm uppercase text-cobweb-pink-light mb-2">
        How CobWeb Works
      </h1>
      <p className="font-mono text-xs text-gray-500 mb-8">
        Every score on this site is a heuristic over public on-chain data.
        Here is exactly how each one is computed, so you can judge them yourself.
      </p>

      <div className="space-y-6">
        {SECTIONS.map((s) => (
          <section key={s.title} className="border-2 border-cobweb-border bg-cobweb-surface p-4">
            <h2 className="font-pixel text-[10px] uppercase text-cobweb-cyan mb-2">{s.title}</h2>
            <p className="font-mono text-xs leading-relaxed text-gray-400">{s.body}</p>
          </section>
        ))}
      </div>
    </div>
  );
}
