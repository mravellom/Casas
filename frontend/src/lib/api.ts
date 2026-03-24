import type {
  FeedbackStats,
  HealthCheck,
  MarketAverageItem,
  OpportunityItem,
  PaginatedResponse,
  PipelineRun,
  PropertyDetail,
  PropertyListItem,
  SystemMetrics,
} from "./types";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

async function apiFetch<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: { "Content-Type": "application/json", ...options?.headers },
  });
  if (!res.ok) throw new Error(`API error: ${res.status}`);
  return res.json();
}

// Properties
export async function getProperties(params?: Record<string, string>) {
  const qs = params ? "?" + new URLSearchParams(params).toString() : "";
  return apiFetch<PaginatedResponse<PropertyListItem>>(`/api/v1/properties${qs}`);
}

export async function getProperty(id: string) {
  return apiFetch<PropertyDetail>(`/api/v1/properties/${id}`);
}

// Opportunities
export async function getOpportunities(params?: Record<string, string>) {
  const qs = params ? "?" + new URLSearchParams(params).toString() : "";
  return apiFetch<PaginatedResponse<OpportunityItem>>(`/api/v1/opportunities${qs}`);
}

export async function getTopOpportunities(limit = 10) {
  return apiFetch<{ data: OpportunityItem[] }>(`/api/v1/opportunities/top?limit=${limit}`);
}

export async function getMarketAverages(commune?: string) {
  const qs = commune ? `?commune=${encodeURIComponent(commune)}` : "";
  return apiFetch<{ data: MarketAverageItem[] }>(`/api/v1/opportunities/market${qs}`);
}

// Admin
export async function getHealth() {
  return apiFetch<HealthCheck>("/api/v1/admin/health");
}

export async function getMetrics() {
  return apiFetch<SystemMetrics>("/api/v1/admin/metrics");
}

export async function getPipelineLogs(limit = 10) {
  return apiFetch<{ runs: PipelineRun[] }>(`/api/v1/admin/logs?limit=${limit}`);
}

export async function getPipelineStatus() {
  return apiFetch<{ running: boolean; last_run: string | null; last_error: string | null }>(
    "/api/v1/admin/scrape/status"
  );
}

export async function triggerPipeline() {
  return apiFetch<{ status: string; message: string }>("/api/v1/admin/scrape/trigger", {
    method: "POST",
  });
}

export async function getFeedbackStats() {
  return apiFetch<FeedbackStats>("/api/v1/admin/feedback/stats");
}
