export interface PropertyListItem {
  id: string;
  source: string;
  source_url: string;
  title: string;
  price_uf: number | null;
  price_m2_uf: number | null;
  m2_total: number | null;
  bedrooms: number | null;
  bathrooms: number | null;
  commune: string;
  address: string | null;
  latitude: number | null;
  longitude: number | null;
  is_opportunity: boolean;
  is_direct_owner: boolean;
  opportunity_score: number | null;
  first_seen_at: string | null;
}

export interface PropertyDetail extends PropertyListItem {
  description: string | null;
  price_clp: number | null;
  m2_util: number | null;
  latitude: number | null;
  longitude: number | null;
  floor: number | null;
  has_parking: boolean | null;
  has_bodega: boolean | null;
  has_urgency_keyword: boolean;
  is_active: boolean;
  rentability: RentabilityData | null;
  neighborhood: NeighborhoodData | null;
  is_direct_owner: boolean;
  last_seen_at: string | null;
  images: string[] | null;
  source_id: string;
}

export interface RentabilityData {
  estimated_rent_uf: number;
  cap_rate: number;
  cap_rate_net: number;
  payback_years: number;
  roi_annual: number;
  monthly_expenses_uf: number;
  monthly_cashflow_uf: number;
  is_high_rentability: boolean;
}

export interface NeighborhoodData {
  nearest_metro: { name: string; distance_m: number; walk_minutes: number } | null;
  services_500m: { supermarkets: number; pharmacies: number; parks: number };
  future_metro: { line: string; name: string; distance_m: number; walk_minutes: number } | null;
  connectivity_score: number;
  is_master_buy: boolean;
}

export interface OpportunityItem {
  id: string;
  source: string;
  source_url: string;
  title: string;
  price_uf: number | null;
  price_m2_uf: number | null;
  m2_total: number | null;
  bedrooms: number | null;
  commune: string;
  opportunity_score: number | null;
  has_urgency_keyword: boolean;
  pct_below_market: number | null;
  avg_zone_price_m2: number | null;
  estimated_market_value_uf: number | null;
  potential_profit_uf: number | null;
  first_seen_at: string | null;
}

export interface MarketAverageItem {
  commune: string;
  bedrooms: number;
  avg_price_m2_uf: number;
  median_price_m2_uf: number | null;
  min_price_m2_uf: number | null;
  max_price_m2_uf: number | null;
  sample_count: number;
  last_updated: string | null;
}

export interface PaginatedResponse<T> {
  total: number;
  page: number;
  limit: number;
  data: T[];
}

export interface SystemMetrics {
  timestamp: string;
  properties: {
    total_active: number;
    new_today: number;
    by_source: Record<string, number>;
    by_commune: Record<string, number>;
  };
  opportunities: { active: number; detected_today: number };
  users: { total: number; active: number };
  alerts: { sent_today: number; sent_this_week: number };
  pipeline: { last_runs: PipelineRun[] };
}

export interface PipelineRun {
  timestamp: string;
  status: string;
  properties_found: number;
  opportunities_found: number;
  alerts_sent: number;
  errors: string[];
  duration_seconds: number;
}

export interface FeedbackStats {
  total_feedback: number;
  good: number;
  bad: number;
  false_positive_rate: number | null;
  target: string;
  status: string;
}

export interface HealthCheck {
  status: string;
  service: string;
  version: string;
  timestamp: string;
  database: string;
  properties_in_db: number;
}
