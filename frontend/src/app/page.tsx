'use client';

import { useRouter } from 'next/navigation';
import { useState, FormEvent } from 'react';
import { Input } from '@/components/ui/Input';
import { Button } from '@/components/ui/Button';
import { Search, Zap, Network, Shield } from 'lucide-react';
import { CobyGreeting } from '@/components/mascot/CobyGreeting';

const DEMO_CAS = [
  'So11111111111111111111111111111111111111112',
  'EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v',
];

const FEATURES = [
  {
    icon: Network,
    title: 'Cabal Detector',
    desc: 'Interactive web graph of wallet connections — shared funders, transfers, co-trading.',
  },
  {
    icon: Zap,
    title: 'Smart Money',
    desc: 'Archetype classification filters bots and surfaces wallets with real conviction.',
  },
  {
    icon: Shield,
    title: 'Dev Risk Score',
    desc: 'Deployer history — serial launches, quick sells, and rug patterns.',
  },
];

const STEPS = [
  { step: '01', text: 'Enter a token contract address' },
  { step: '02', text: 'Find the earliest real buyers' },
  { step: '03', text: 'Cluster, bot, or Smart Money?' },
];

export default function HomePage() {
  const router = useRouter();
  const [ca, setCa] = useState('');

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    const trimmed = ca.trim();
    if (trimmed.length >= 32) {
      router.push(`/token/${trimmed}`);
    }
  };

  return (
    <div className="mx-auto max-w-4xl px-4 py-14 sm:py-20">
      {/* Hero */}
      <section className="text-center animate-fade-up">
        <div className="mb-8 flex justify-center">
          <CobyGreeting />
        </div>

        <span className="eyebrow">Solana On-Chain Analytics</span>

        <h1 className="mt-3 font-pixel text-2xl leading-[1.6] text-white sm:text-3xl sm:leading-[1.6]">
          Who bought early &mdash;
          <br />
          <span className="text-cobweb-pink-light">insiders or smart money?</span>
        </h1>

        <p className="mx-auto mt-5 max-w-xl font-mono text-sm leading-relaxed text-cobweb-muted">
          Paste a token contract address. CobWeb finds the earliest buyers, maps coordinated
          wallet clusters, and scores dev risk &mdash; entirely from on-chain data.
        </p>

        <form onSubmit={handleSubmit} className="mx-auto mt-10 max-w-2xl">
          <div className="flex flex-col gap-2 sm:flex-row">
            <Input
              value={ca}
              onChange={(e) => setCa(e.target.value)}
              placeholder="Paste token contract address (CA)..."
              className="flex-1 text-base"
              spellCheck={false}
            />
            <Button type="submit" className="shrink-0 py-3">
              <Search className="h-4 w-4" />
              Analyze
            </Button>
          </div>
        </form>

        <div className="mt-4 flex flex-wrap items-center justify-center gap-2">
          <span className="font-mono text-[10px] text-gray-600">Try:</span>
          {DEMO_CAS.map((demo) => (
            <button
              key={demo}
              type="button"
              onClick={() => setCa(demo)}
              className="font-mono text-[10px] text-cobweb-cyan transition-colors hover:text-cobweb-pink-light hover:underline"
            >
              {demo.slice(0, 6)}&hellip;{demo.slice(-4)}
            </button>
          ))}
        </div>
      </section>

      {/* Features */}
      <section className="mt-20 grid gap-5 sm:grid-cols-3">
        {FEATURES.map(({ icon: Icon, title, desc }) => (
          <div
            key={title}
            className="pixel-card group p-5 transition-all hover:-translate-y-1 hover:border-cobweb-pink/50"
          >
            <div className="mb-3 inline-flex border-2 border-cobweb-border-soft bg-cobweb-bg-soft p-2 transition-colors group-hover:border-cobweb-pink/50">
              <Icon className="h-5 w-5 text-cobweb-pink" />
            </div>
            <h3 className="mb-2 font-pixel text-[9px] uppercase tracking-wider text-cobweb-pink-light">
              {title}
            </h3>
            <p className="font-mono text-xs leading-relaxed text-cobweb-muted">{desc}</p>
          </div>
        ))}
      </section>

      {/* How it works */}
      <section className="mt-20">
        <div className="mb-8 text-center">
          <span className="eyebrow">The Flow</span>
          <h2 className="mt-2 font-pixel text-xs uppercase text-gray-300">How It Works</h2>
        </div>
        <div className="grid gap-6 sm:grid-cols-3">
          {STEPS.map(({ step, text }, i) => (
            <div key={step} className="relative text-center">
              <div className="mx-auto mb-3 flex h-12 w-12 items-center justify-center border-2 border-cobweb-pink bg-cobweb-bg font-pixel text-sm text-cobweb-pink-light shadow-pixel-sm">
                {step}
              </div>
              <p className="font-mono text-sm text-gray-300">{text}</p>
              {i < STEPS.length - 1 && (
                <span className="pointer-events-none absolute right-0 top-6 hidden translate-x-1/2 font-mono text-cobweb-border sm:block">
                  &rarr;
                </span>
              )}
            </div>
          ))}
        </div>
      </section>

    </div>
  );
}
