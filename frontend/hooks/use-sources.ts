"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api } from "@/lib/api";

export function useSources(projectId: string) {
  return useQuery({
    queryKey: ["sources", projectId],
    queryFn: () => api.listSources(projectId),
    enabled: Boolean(projectId),
    refetchInterval: 10_000
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
    refetchInterval: 10_000
  });
}
