"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api } from "@/lib/api";
import { Source, SourceStatus } from "@/types/source";

function hasActiveSourceStatuses(sources: Source[] | undefined) {
  if (!sources?.length) {
    return false;
  }
  const activeStatuses: SourceStatus[] = ["pending", "indexing"];
  return sources.some((source) => activeStatuses.includes(source.status));
}

function hasActiveIndexing(statusBreakdown: Record<string, number> | undefined) {
  if (!statusBreakdown) {
    return false;
  }
  return ["pending", "indexing"].some((status) => (statusBreakdown[status] ?? 0) > 0);
}

export function useSources(projectId: string, options?: { poll?: boolean }) {
  return useQuery({
    queryKey: ["sources", projectId],
    queryFn: () => api.listSources(projectId),
    enabled: Boolean(projectId),
    staleTime: 30_000,
    refetchInterval: (query) => {
      if (!options?.poll) {
        return false;
      }
      return hasActiveSourceStatuses(query.state.data as Source[] | undefined) ? 3_000 : false;
    }
  });
}

export function useAddSources(projectId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (urls: string[]) => api.addSources(projectId, urls),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["sources", projectId] });
      queryClient.invalidateQueries({ queryKey: ["projects", projectId] });
    }
  });
}

export function useValidateSources() {
  return useMutation({
    mutationFn: (urls: string[]) => api.validateSources(urls)
  });
}

export function useStartIndexing(projectId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () => api.startIndexing(projectId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["sources", projectId] });
      queryClient.invalidateQueries({ queryKey: ["projects", projectId] });
    }
  });
}

export function useIndexStatus(projectId: string) {
  return useQuery({
    queryKey: ["index-status", projectId],
    queryFn: () => api.getIndexStatus(projectId),
    enabled: Boolean(projectId),
    staleTime: 5_000,
    refetchInterval: (query) => {
      const data = query.state.data as { status_breakdown?: Record<string, number> } | undefined;
      return hasActiveIndexing(data?.status_breakdown) ? 3_000 : false;
    }
  });
}
