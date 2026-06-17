'use client';

import { useQuery } from '@tanstack/react-query';
import { useParams } from 'next/navigation';
import { api } from '@/lib/api';
import { TokenDashboard } from '@/components/token/TokenDashboard';
import { LoadingSpinner } from '@/components/ui/Loading';
import { Button } from '@/components/ui/Button';
import Link from 'next/link';

export default function TokenPage() {
  const params = useParams();
  const ca = params.ca as string;

  // Fast pass: metadata + early buyers + entry mcap. Renders in seconds.
  const fastQuery = useQuery({
    queryKey: ['token', ca, 'fast'],
    queryFn: () => api.getToken(ca, false),
    enabled: !!ca,
    staleTime: 60_000,
  });

  // Deep pass: cabal clusters + dev risk. Can take 30-60s on cold cache —
  // runs in the background while the user already sees the fast data.
  const deepQuery = useQuery({
    queryKey: ['token', ca, 'deep'],
    queryFn: () => api.getToken(ca, true),
    enabled: !!ca,
    staleTime: 60_000,
    retry: 1,
    // If another user triggered the same scan, the API returns the fast
    // version (analysis_complete=false) while the shared computation runs —
    // poll until the deep result lands in the shared cache.
    refetchInterval: (query) =>
      query.state.data && query.state.data.analysis_complete === false ? 4_000 : false,
  });

  const data = deepQuery.data ?? fastQuery.data;
  const isLoading = !data && (fastQuery.isLoading || deepQuery.isLoading);
  const error = !data ? (deepQuery.error ?? fastQuery.error) : null;
  const analyzing =
    (!deepQuery.data && !deepQuery.error) ||
    deepQuery.data?.analysis_complete === false;

  return (
    <div className="mx-auto max-w-7xl px-4 py-8">
      <div className="mb-6">
        <Link href="/" className="font-pixel text-[8px] uppercase text-gray-500 hover:text-cobweb-pink-light">
          ← Back to search
        </Link>
      </div>

      {isLoading && <LoadingSpinner label="Analyzing token on-chain..." />}

      {error != null && (
        <div className="pixel-card p-8 text-center">
          <p className="font-pixel text-[10px] uppercase text-cobweb-red mb-4">
            Analysis Failed
          </p>
          <p className="font-mono text-sm text-gray-400 mb-6">
            {error instanceof Error ? error.message : 'Could not fetch token data. Is the backend running?'}
          </p>
          <div className="flex justify-center gap-3">
            <Button onClick={() => { fastQuery.refetch(); deepQuery.refetch(); }}>Retry</Button>
            <Link href="/">
              <Button variant="ghost">Go Home</Button>
            </Link>
          </div>
        </div>
      )}

      {data && <TokenDashboard data={data} analyzing={analyzing} />}
    </div>
  );
}
