"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api } from "@/lib/api";
import { AnalysisCreatePayload } from "@/types/analytics";

export function useRunAnalysis(projectId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: AnalysisCreatePayload) => api.runAnalysis(projectId, payload),
    onSuccess: (run) => {
      queryClient.invalidateQueries({ queryKey: ["analysis-run", run.id] });
    }
  });
}

export function useAnalysisRun(analysisRunId?: string) {
  return useQuery({
    queryKey: ["analysis-run", analysisRunId],
    queryFn: () => api.getAnalysisRun(analysisRunId as string),
    enabled: Boolean(analysisRunId),
    refetchInterval: (query) => {
      const status = (query.state.data as { status?: string } | undefined)?.status;
      return status && ["pending", "running"].includes(status) ? 4000 : false;
    }
  });
}

export function useReport(analysisRunId?: string, enabled = true) {
  return useQuery({
    queryKey: ["report", analysisRunId],
    queryFn: () => api.getReport(analysisRunId as string),
    enabled: Boolean(analysisRunId) && enabled,
    retry: false
  });
}

export function useReportsTree() {
  return useQuery({
    queryKey: ["reports-tree"],
    queryFn: api.listReportsTree,
    staleTime: 15_000,
    refetchInterval: 30_000
  });
}

export function useDeleteReport() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: api.deleteReport,
    onSuccess: (_data, analysisRunId) => {
      queryClient.invalidateQueries({ queryKey: ["reports-tree"] });
      queryClient.removeQueries({ queryKey: ["report", analysisRunId] });
      queryClient.removeQueries({ queryKey: ["analysis-run", analysisRunId] });
    }
  });
}
