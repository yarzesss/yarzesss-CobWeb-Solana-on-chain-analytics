'use client';

import { useEffect, useState } from 'react';

/**
 * Coby — the CobWeb pixel-spider mascot.
 *
 * Built on a strict pixel grid (each "pixel" is a 6×6 unit rect) so it
 * stays crisp at any size and matches the site's pixel-art language.
 * Motion is deliberately minimal & solid:
 *   - hangs from a thread that gently breathes (coby-thread / coby-bob)
 *   - blinks every few seconds
 *   - gives a small one-time wave on mount (greeting)
 * Respects prefers-reduced-motion.
 */

const P = 6; // pixel unit

function px(x: number, y: number, fill: string, w = 1, h = 1) {
  return <rect key={`${x}-${y}-${fill}`} x={x * P} y={y * P} width={w * P} height={h * P} fill={fill} />;
}

export function Coby({ size = 96, className = '' }: { size?: number; className?: string }) {
  const [blink, setBlink] = useState(false);
  const [waving, setWaving] = useState(true);

  useEffect(() => {
    // greeting wave, then settle
    const settle = setTimeout(() => setWaving(false), 1400);
    // blink loop
    const blinkLoop = setInterval(() => {
      setBlink(true);
      setTimeout(() => setBlink(false), 160);
    }, 3800);
    return () => {
      clearTimeout(settle);
      clearInterval(blinkLoop);
    };
  }, []);

  const body = '#15152a';
  const bodyHi = '#1f1f3a';
  const outline = '#34344f';
  const pink = '#E91E8C';
  const eyeWhite = '#e8e8f5';
  const eyeDark = '#0b0b14';

  // grid is 16 wide; thread drops from top center
  return (
    <div
      className={`inline-block ${className}`}
      style={{ width: size, height: size }}
      aria-label="Coby the spider mascot"
      role="img"
    >
      <svg
        viewBox="0 0 96 108"
        width={size}
        height={size * (108 / 96)}
        xmlns="http://www.w3.org/2000/svg"
        shapeRendering="crispEdges"
        style={{ overflow: 'visible' }}
      >
        {/* hanging thread */}
        <g
          className="motion-safe:animate-coby-thread"
          style={{ transformOrigin: '48px 0px' }}
        >
          <rect x={47} y={0} width={2} height={18} fill={outline} />
        </g>

        {/* the spider bobs as one unit */}
        <g className="motion-safe:animate-coby-bob" style={{ transformOrigin: '48px 54px' }}>
          {/* legs — left */}
          {px(1, 9, outline)}{px(2, 8, outline)}{px(3, 9, outline)}
          {px(1, 11, outline)}{px(2, 12, outline)}{px(3, 11, outline)}
          {/* legs — right (the top one waves) */}
          <g
            className={waving ? 'origin-bottom-left motion-safe:[animation:coby-bob_0.5s_ease-in-out_2]' : ''}
            style={{ transformOrigin: '13px 9px' }}
          >
            {px(12, 8, pink)}{px(13, 7, pink)}{px(14, 8, pink)}
          </g>
          {px(12, 11, outline)}{px(13, 12, outline)}{px(14, 11, outline)}

          {/* body outline ring */}
          {px(5, 6, outline, 6, 1)}
          {px(5, 13, outline, 6, 1)}
          {px(4, 7, outline, 1, 6)}
          {px(11, 7, outline, 1, 6)}

          {/* body fill */}
          {px(5, 7, body, 6, 6)}
          {px(5, 7, bodyHi, 6, 2)}

          {/* eyes */}
          {blink ? (
            <>
              {px(6, 10, eyeDark, 2, 1)}
              {px(9, 10, eyeDark, 2, 1)}
            </>
          ) : (
            <>
              {px(6, 9, eyeWhite, 2, 2)}
              {px(9, 9, eyeWhite, 2, 2)}
              {px(7, 10, eyeDark)}
              {px(10, 10, eyeDark)}
            </>
          )}

          {/* little smile */}
          {px(7, 12, pink, 3, 1)}
        </g>
      </svg>
    </div>
  );
}
