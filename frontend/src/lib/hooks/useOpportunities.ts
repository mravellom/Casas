"use client";
import { useQuery } from "@tanstack/react-query";
import { getOpportunities, getTopOpportunities, getMarketAverages } from "../api";

export function useOpportunities(params?: Record<string, string>) {
  return useQuery({
    queryKey: ["opportunities", params],
    queryFn: () => getOpportunities(params),
    refetchInterval: 60000,
  });
}

export function useTopOpportunities(limit = 10) {
  return useQuery({
    queryKey: ["top-opportunities", limit],
    queryFn: () => getTopOpportunities(limit),
    refetchInterval: 60000,
  });
}

export function useMarketAverages(commune?: string) {
  return useQuery({
    queryKey: ["market-averages", commune],
    queryFn: () => getMarketAverages(commune),
  });
}
