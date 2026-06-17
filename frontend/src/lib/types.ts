export type Archetype =
  | 'sniper'
  | 'insider'
  | 'swing'
  | 'swing_trader'
  | 'accumulator'
  | 'flipper'
  | 'bot'
  | 'unknown';

export type DevRiskLevel = 'LOW' | 'MEDIUM' | 'HIGH';

export type LifecycleStage =
  | 'accumulation'
  | 'markup'
  | 'distribution'
  | 'dump'
  | 'unknown';

export type BuyerCategory = 'smart_money' | 'bot' | 'cluster' | 'regular';

export interface EarlyBuyer {
  wallet: string;
  timestamp?: number;
  tx_signature?: string;
  slot?: number;
  /** Tokens bought (decimals-adjusted) */
  amount?: number;
  amount_tokens?: number;
  /** Position size in USD at entry */
  amount_usd?: number | null;
  sol_spent?: number;
  entry_price_sol?: number | null;
  /** Market cap at the moment of entry */
  entry_market_cap_usd?: number | null;
  market_cap_usd?: number | null;
  blocks_after_launch?: number;
  bot_score?: number;
  smart_money_score?: number;
  archetype?: Archetype;
  category?: BuyerCategory;
  in_cluster?: boolean;
  cluster_id?: number | null;
  suspicion_score?: number | null;
  cluster_type?: string | null;
}

export interface CabalConnection {
  from: string;
  to: string;
  type: 'funding' | 'direct_transfer' | string;
  amount_sol?: number;
}

export interface CabalCluster {
  wallets: string[];
  connections: CabalConnection[];
  common_funder: string | null;
  suspicion_score: number;
  co_traded_tokens?: string[];
}

export interface CabalData {
  clusters: CabalCluster[];
  independent_wallets: string[];
}

export interface DevRisk {
  score: number;
  level: DevRiskLevel;
  dev_wallet: string | null;
  dev_prev_tokens?: number;
  quick_sell_signal?: boolean;
  /** true while the fast (deep=false) pass hasn't computed dev risk yet */
  pending?: boolean;
}

export interface TokenAnalysis {
  ca: string;
  name: string | null;
  symbol: string | null;
  token_supply?: number;
  sol_price_usd?: number;
  early_buyers_count: number;
  buyer_counts?: {
    smart_money: number;
    bots: number;
    cluster_members: number;
    regular: number;
  };
  early_buyers: EarlyBuyer[];
  cabal: CabalData;
  dev_risk: DevRisk;
  lifecycle?: TokenLifecycle;
  market?: TokenMarket;
  holders?: TokenHolders;
  /** 'index' = exact data from the realtime webhook index; 'history' = reconstructed */
  buyers_source?: 'index' | 'history';
  /** false on the fast pass (deep=false) — cabal & dev risk still computing */
  analysis_complete?: boolean;
}

export interface TokenMarket {
  price_usd?: number | null;
  market_cap_usd?: number | null;
  liquidity_usd?: number | null;
  volume_24h_usd?: number | null;
  dex?: string | null;
  venue?: 'amm' | 'bonding_curve' | 'unknown';
  source?: 'dexscreener' | 'onchain_trades' | 'none';
  pending?: boolean;
}

export interface TokenHolders {
  top10_pct: number | null;
  top_holders: Array<{ address: string; amount: number; pct: number | null }>;
}

export interface TokenLifecycle {
  stage: 'accumulation' | 'markup' | 'distribution' | 'dump' | 'unknown';
  buy_count?: number;
  sell_count?: number;
  unique_buyers?: number;
  unique_sellers?: number;
  window_trades?: number;
  pending?: boolean;
}

// ── Auth & demo copy-trade competition ──

export interface AuthResponse {
  access_token: string;
  token_type: string;
  nickname: string;
}

export interface OpenPosition {
  mint: string;
  source_wallet: string;
  invested_usd: number;
  current_value_usd: number;
  unrealized_pnl_usd: number;
  entry_price_usd: number;
  current_price_usd: number | null;
  opened_at: number;
  priced: boolean;
}

export interface AccountSnapshot {
  nickname: string;
  balance_usd: number;
  open_value_usd: number;
  equity_usd: number;
  starting_balance_usd: number;
  total_pnl_usd: number;
  total_pnl_pct: number;
  realized_pnl_usd: number;
  position_size_usd: number;
  closed_trades: number;
  winning_trades: number;
  winrate: number;
  open_positions: OpenPosition[];
}

export interface ServerWatchItem {
  wallet: string;
  label: string | null;
  added_at: string | null;
}

export interface CompetitionEntry {
  rank: number;
  nickname: string;
  equity_usd: number;
  total_pnl_usd: number;
  total_pnl_pct: number;
  realized_pnl_usd: number;
  closed_trades: number;
  winrate: number;
}

export interface CompetitionLeaderboard {
  entries: CompetitionEntry[];
  active: boolean;
  message: string | null;
}

export interface WalletProfile {
  wallet_address: string;
  archetype: Archetype;
  bot_score: number;
  smart_money_score: number;
  winrate: number;
  total_trades: number;
  total_pnl_usd: number;
  avg_position_size_usd: number;
  avg_hold_time_minutes: number;
  favorite_dex: string | null;
  first_seen: string | null;
  last_active: string | null;
  updated_at: string;
}

export interface WalletPnl {
  wallet_address: string;
  summary: {
    total_sol_pnl?: number;
    total_realized_usd: number;
    total_unrealized_usd?: number;
    winrate: number;
    total_trades: number;
    completed_trades?: number;
    win_trades?: number;
    avg_hold_time_minutes: number;
    avg_position_size_usd: number;
    avg_position_size_sol?: number;
    favorite_dex?: string | null;
    sol_price_usd?: number;
    unpriced_positions?: number;
  };
  by_token?: Array<{
    mint: string;
    symbol?: string;
    realized_usd: number;
    sol_pnl?: number;
    sol_spent?: number;
    sol_received?: number;
    buys?: number;
    sells?: number;
    trades: number;
    holding?: number;
    unrealized_usd?: number | null;
  }>;
}

export interface TradeRecord {
  signature?: string;
  timestamp?: number;
  type?: string;
  source?: string;
  description?: string;
  tokenTransfers?: Array<Record<string, unknown>>;
}

export interface GraphNode {
  id: string;
  label: string;
  group: 'funder' | 'member' | 'independent';
  suspicionScore?: number;
}

export interface GraphLink {
  source: string;
  target: string;
  type: string;
  amount_sol?: number;
}
