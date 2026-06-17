import Link from 'next/link';

export function Footer() {
  return (
    <footer className="mt-20 border-t-2 border-cobweb-border-soft">
      <div className="mx-auto flex max-w-7xl flex-col items-center justify-between gap-4 px-4 py-8 sm:flex-row">
        <div className="flex items-center gap-2">
          <span className="font-pixel text-[10px] text-cobweb-pink-light">COBWEB</span>
          <span className="font-mono text-[10px] text-gray-600">on-chain intelligence</span>
        </div>
        <nav className="flex items-center gap-4 font-mono text-[10px] text-gray-500">
          <Link href="/methodology" className="transition-colors hover:text-cobweb-cyan">
            How it works
          </Link>
          <Link href="/leaderboard" className="transition-colors hover:text-cobweb-cyan">
            Leaderboard
          </Link>
          <span className="text-gray-700">·</span>
          <span>Data from Solana &amp; Helius. Not financial advice.</span>
        </nav>
      </div>
    </footer>
  );
}
