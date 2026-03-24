"use client";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  getMetrics,
  getPipelineLogs,
  getPipelineStatus,
  triggerPipeline,
  getFeedbackStats,
  getHealth,
} from "../api";

export function useHealth() {
  return useQuery({ queryKey: ["health"], queryFn: getHealth, refetchInterval: 30000 });
}

export function useMetrics() {
  return useQuery({ queryKey: ["metrics"], queryFn: getMetrics, refetchInterval: 30000 });
}

export function usePipelineLogs(limit = 10) {
  return useQuery({ queryKey: ["pipeline-logs", limit], queryFn: () => getPipelineLogs(limit) });
}

export function usePipelineStatus() {
  return useQuery({ queryKey: ["pipeline-status"], queryFn: getPipelineStatus, refetchInterval: 5000 });
}

export function useTriggerPipeline() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: triggerPipeline,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["pipeline-status"] });
    },
  });
}

export function useFeedbackStats() {
  return useQuery({ queryKey: ["feedback-stats"], queryFn: getFeedbackStats });
}
