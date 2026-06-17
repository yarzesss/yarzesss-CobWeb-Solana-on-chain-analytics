import type {
  AuthResponse,
  AccountSnapshot,
  CompetitionLeaderboard,
  ServerWatchItem,
  CabalData,
  DevRisk,
  GraphLink,
  GraphNode,
  TokenAnalysis,
  WalletPnl,
  WalletProfile,
  TradeRecord,
  EarlyBuyer,
} from './types';

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000';

const TOKEN_KEY = 'cobweb_token';

export function getToken(): string | null {
  if (typeof window === 'undefined') return null;
  return localStorage.getItem(TOKEN_KEY);
}
export function setToken(token: string | null) {
  if (typeof window === 'undefined') return;
  if (token) localStorage.setItem(TOKEN_KEY, token);
  else localStorage.removeItem(TOKEN_KEY);
}

class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
    this.name = 'ApiError';
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const token = getToken();
  const res = await fetch(`${API_URL}${path}`, {
    ...init,
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...init?.headers,
    },
  });

  if (!res.ok) {
    const body = await res.text();
    throw new ApiError(res.status, body || res.statusText);
  }

  return res.json() as Promise<T>;
}

export const api = {
  health: () => request<{ status: string }>('/healthz'),


  getToken: (ca: string, deep = true) =>
    request<TokenAnalysis>(`/token/${ca}?deep=${deep}`),
  // ── Auth ──
  register: (nickname: string, password: string) =>
    request<AuthResponse>('/auth/register', {
      method: 'POST',
      body: JSON.stringify({ nickname, password }),
    }),
  login: (nickname: string, password: string) =>
    request<AuthResponse>('/auth/login', {
      method: 'POST',
      body: JSON.stringify({ nickname, password }),
    }),
  me: () => request<{ user_id: number; nickname: string }>('/auth/me'),

  // ── Account / copy-trade ──
  getAccount: () => request<AccountSnapshot>('/account'),
  setPositionSize: (size: number) =>
    request<{ position_size_usd: number }>('/account/position-size', {
      method: 'PUT',
      body: JSON.stringify({ position_size_usd: size }),
    }),
  resetAccount: () =>
    request<{ balance_usd: number; reset: boolean }>('/account/reset', { method: 'POST' }),

  // ── Server-side watchlist (drives the bot) ──
  getWatchlist: () => request<ServerWatchItem[]>('/account/watchlist'),
  addWatch: (wallet: string, label?: string) =>
    request<{ wallet: string; added: boolean }>('/account/watchlist', {
      method: 'POST',
      body: JSON.stringify({ wallet, label: label ?? null }),
    }),
  removeWatch: (wallet: string) =>
    request<{ wallet: string; removed: boolean }>(`/account/watchlist/${wallet}`, {
      method: 'DELETE',
    }),

  // ── Competition leaderboard ──
  getLeaderboard: () => request<CompetitionLeaderboard>('/leaderboard'),

  getTokenEarlyBuyers: (ca: string, limit = 100, offset = 0) =>
    request<{ ca: string; total: number; buyers: EarlyBuyer[] }>(
      `/token/${ca}/early-buyers?limit=${limit}&offset=${offset}`,
    ),

  getTokenCabal: (ca: string) =>
    request<CabalData>(`/token/${ca}/cabal`),

  getTokenDevRisk: (ca: string) =>
    request<DevRisk>(`/token/${ca}/dev-risk`),

  getWallet: (address: string) =>
    request<WalletProfile>(`/wallet/${address}`),

  getWalletTrades: (address: string, limit = 100, offset = 0) =>
    request<{
      wallet_address: string;
      total: number;
      trades: TradeRecord[];
    }>(`/wallet/${address}/trades?limit=${limit}&offset=${offset}`),

  getWalletPnl: (address: string) =>
    request<WalletPnl>(`/wallet/${address}/pnl`),

};

export function cabalToGraph(cabal: CabalData): {
  nodes: GraphNode[];
  links: GraphLink[];
} {
  const nodeMap = new Map<string, GraphNode>();
  const links: GraphLink[] = [];

  const ensureNode = (
    id: string,
    group: GraphNode['group'],
    suspicionScore?: number,
  ) => {
    if (!nodeMap.has(id)) {
      nodeMap.set(id, {
        id,
        label: id.slice(0, 4) + '…' + id.slice(-4),
        group,
        suspicionScore,
      });
    }
  };

  for (const cluster of cabal.clusters) {
    for (const wallet of cluster.wallets) {
      ensureNode(wallet, 'member', cluster.suspicion_score);
    }
    if (cluster.common_funder) {
      ensureNode(cluster.common_funder, 'funder', cluster.suspicion_score);
    }
    for (const conn of cluster.connections) {
      links.push({
        source: conn.from,
        target: conn.to,
        type: conn.type,
        amount_sol: conn.amount_sol,
      });
    }
  }

  for (const wallet of cabal.independent_wallets) {
    ensureNode(wallet, 'independent');
  }

  return { nodes: Array.from(nodeMap.values()), links };
}

export { ApiError };
