'use client';

import { useEffect, useState } from 'react';
import { Coby } from './Coby';

const GREETINGS = [
  "Hi, I'm Coby. Paste a token and I'll untangle its web.",
  'Drop a contract address — let me see who got in early.',
  'Smart money or a coordinated cabal? Let me check.',
  'Show me a token. I read the on-chain threads.',
];

export function CobyGreeting() {
  const [line, setLine] = useState(GREETINGS[0]);
  const [show, setShow] = useState(false);

  useEffect(() => {
    setLine(GREETINGS[Math.floor(Math.random() * GREETINGS.length)]);
    const t = setTimeout(() => setShow(true), 250);
    return () => clearTimeout(t);
  }, []);

  return (
    <div className="flex items-end justify-center gap-3">
      <Coby size={84} />
      <div
        className={`relative mb-2 max-w-xs border-2 border-cobweb-border bg-cobweb-surface px-3 py-2 transition-all duration-500 ${
          show ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-1'
        }`}
      >
        {/* bubble tail */}
        <span className="absolute -left-2 bottom-3 h-0 w-0 border-y-8 border-r-8 border-y-transparent border-r-cobweb-border" />
        <p className="font-mono text-xs leading-relaxed text-gray-300">{line}</p>
      </div>
    </div>
  );
}
