'use client';

import { useEffect, useMemo, useRef, useState, useCallback } from 'react';
import type { CabalData } from '@/lib/types';
import { cabalToGraph } from '@/lib/api';
import { GraphLegend, NodeDetailPanel, type SelectedNode } from './NodeDetailPanel';

const NODE_COLORS: Record<string, string> = {
  funder: '#ef4444',
  member: '#C2185B',
  independent: '#4ade80',
};

const W = 900;
const H = 440;

interface SimNode {
  id: string;
  label: string;
  group: 'funder' | 'member' | 'independent';
  suspicionScore?: number;
  x: number;
  y: number;
  vx: number;
  vy: number;
}

interface SimLink {
  source: string;
  target: string;
  type: string;
  amount_sol?: number;
}

/**
 * Self-contained force-directed graph on plain SVG.
 *
 * Replaces react-force-graph (which silently failed to start its d3
 * simulation under Next.js, leaving a static spiral with no links).
 * No external graph/three deps — just a tiny Verlet-ish integrator:
 *   - repulsion between all nodes (Coulomb-like)
 *   - spring attraction along links
 *   - gentle pull to center
 * Runs ~250 ticks then settles; user can drag nodes and pan/zoom.
 */
export function CabalGraph2D({ cabal }: { cabal: CabalData }) {
  const { nodes: rawNodes, links: rawLinks } = useMemo(
    () => cabalToGraph(cabal),
    [cabal],
  );

  const [selected, setSelected] = useState<SelectedNode | null>(null);
  const [, force] = useState(0); // re-render trigger
  const nodesRef = useRef<SimNode[]>([]);
  const draggingRef = useRef<string | null>(null);
  const svgRef = useRef<SVGSVGElement | null>(null);
  const frameRef = useRef<number>(0);

  // (Re)initialise simulation whenever the data changes
  useEffect(() => {
    const n = rawNodes.length;
    if (n === 0) {
      nodesRef.current = [];
      return;
    }
    // seed on a circle (not a line) so forces have something to expand
    nodesRef.current = rawNodes.map((node, i) => {
      const angle = (i / n) * Math.PI * 2;
      const r = Math.min(W, H) * 0.32;
      return {
        id: node.id,
        label: node.label,
        group: node.group,
        suspicionScore: node.suspicionScore,
        x: W / 2 + Math.cos(angle) * r,
        y: H / 2 + Math.sin(angle) * r,
        vx: 0,
        vy: 0,
      };
    });

    const idx = new Map(nodesRef.current.map((nd, i) => [nd.id, i]));
    const linkPairs = rawLinks
      .map((l) => ({
        s: idx.get(typeof l.source === 'string' ? l.source : String(l.source)),
        t: idx.get(typeof l.target === 'string' ? l.target : String(l.target)),
      }))
      .filter((l): l is { s: number; t: number } => l.s != null && l.t != null);

    let ticks = 0;
    const maxTicks = 260;

    const tick = () => {
      const arr = nodesRef.current;
      const N = arr.length;

      // repulsion (O(n^2) — fine for <200 nodes)
      for (let i = 0; i < N; i++) {
        for (let j = i + 1; j < N; j++) {
          let dx = arr[i].x - arr[j].x;
          let dy = arr[i].y - arr[j].y;
          let dist2 = dx * dx + dy * dy;
          if (dist2 < 1) dist2 = 1;
          const dist = Math.sqrt(dist2);
          const repel = 1400 / dist2;
          const fx = (dx / dist) * repel;
          const fy = (dy / dist) * repel;
          arr[i].vx += fx;
          arr[i].vy += fy;
          arr[j].vx -= fx;
          arr[j].vy -= fy;
        }
      }

      // spring attraction along links
      for (const { s, t } of linkPairs) {
        const a = arr[s];
        const b = arr[t];
        const dx = b.x - a.x;
        const dy = b.y - a.y;
        const dist = Math.sqrt(dx * dx + dy * dy) || 1;
        const target = 60;
        const k = 0.02 * (dist - target);
        const fx = (dx / dist) * k;
        const fy = (dy / dist) * k;
        a.vx += fx;
        a.vy += fy;
        b.vx -= fx;
        b.vy -= fy;
      }

      // center gravity + integrate + damping
      for (const nd of arr) {
        if (draggingRef.current === nd.id) {
          nd.vx = 0;
          nd.vy = 0;
          continue;
        }
        nd.vx += (W / 2 - nd.x) * 0.002;
        nd.vy += (H / 2 - nd.y) * 0.002;
        nd.vx *= 0.85;
        nd.vy *= 0.85;
        nd.x += nd.vx;
        nd.y += nd.vy;
        nd.x = Math.max(12, Math.min(W - 12, nd.x));
        nd.y = Math.max(12, Math.min(H - 12, nd.y));
      }

      force((v) => v + 1);
      ticks += 1;
      if (ticks < maxTicks) {
        frameRef.current = requestAnimationFrame(tick);
      }
    };

    frameRef.current = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(frameRef.current);
  }, [rawNodes, rawLinks]);

  const posOf = useCallback((id: string) => {
    return nodesRef.current.find((n) => n.id === id);
  }, []);

  // dragging
  const onPointerDown = (id: string) => (e: React.PointerEvent) => {
    e.stopPropagation();
    draggingRef.current = id;
    (e.target as Element).setPointerCapture?.(e.pointerId);
  };
  const onPointerMove = (e: React.PointerEvent) => {
    const id = draggingRef.current;
    if (!id || !svgRef.current) return;
    const rect = svgRef.current.getBoundingClientRect();
    const node = posOf(id);
    if (!node) return;
    node.x = ((e.clientX - rect.left) / rect.width) * W;
    node.y = ((e.clientY - rect.top) / rect.height) * H;
    force((v) => v + 1);
  };
  const onPointerUp = () => {
    draggingRef.current = null;
  };

  if (rawNodes.length === 0) {
    return (
      <div className="flex h-[440px] items-center justify-center border-2 border-cobweb-border bg-[#080812]">
        <p className="font-pixel text-[10px] uppercase text-gray-500">
          No wallet nodes to display
        </p>
      </div>
    );
  }

  const nodes = nodesRef.current;

  return (
    <div className="relative">
      <div className="mb-3 flex items-center justify-between gap-4">
        <GraphLegend />
        <span className="font-mono text-[10px] text-gray-600">
          {nodes.length} nodes · {rawLinks.length} links
        </span>
      </div>

      <div className="relative h-[440px] overflow-hidden border-2 border-cobweb-border bg-[#080812] scanlines">
        <svg
          ref={svgRef}
          viewBox={`0 0 ${W} ${H}`}
          className="h-full w-full touch-none"
          preserveAspectRatio="xMidYMid meet"
          onPointerMove={onPointerMove}
          onPointerUp={onPointerUp}
          onPointerLeave={onPointerUp}
        >
          {/* links */}
          {rawLinks.map((l, i) => {
            const s = posOf(typeof l.source === 'string' ? l.source : String(l.source));
            const t = posOf(typeof l.target === 'string' ? l.target : String(l.target));
            if (!s || !t) return null;
            const color = l.type === 'funding' ? '#fbbf24' : l.type === 'transfer' ? '#22d3ee' : '#5b5b86';
            return (
              <line
                key={`${l.source}-${l.target}-${i}`}
                x1={s.x}
                y1={s.y}
                x2={t.x}
                y2={t.y}
                stroke={color}
                strokeWidth={l.type === 'funding' ? 2 : 1.2}
                strokeOpacity={0.55}
              />
            );
          })}

          {/* nodes — pixel squares */}
          {nodes.map((n) => {
            const size = n.group === 'funder' ? 16 : 12;
            const color = NODE_COLORS[n.group] ?? NODE_COLORS.member;
            return (
              <g
                key={n.id}
                transform={`translate(${n.x},${n.y})`}
                className="cursor-pointer"
                onPointerDown={onPointerDown(n.id)}
                onClick={(e) => {
                  e.stopPropagation();
                  setSelected({
                    id: n.id,
                    group: n.group,
                    suspicionScore: n.suspicionScore,
                  });
                }}
              >
                <rect
                  x={-size / 2}
                  y={-size / 2}
                  width={size}
                  height={size}
                  fill={color}
                  stroke="#0b0b14"
                  strokeWidth={2}
                />
                <rect x={-size / 2 + 2} y={-size / 2 + 2} width={size / 3} height={size / 3} fill="rgba(255,255,255,0.3)" />
              </g>
            );
          })}
        </svg>

        {selected && (
          <NodeDetailPanel
            node={selected}
            links={rawLinks}
            onClose={() => setSelected(null)}
          />
        )}
      </div>

      <p className="mt-2 font-mono text-[10px] text-gray-500">
        Pixel node map — drag nodes to rearrange, click to inspect.
      </p>
    </div>
  );
}
