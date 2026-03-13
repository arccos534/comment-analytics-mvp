"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api } from "@/lib/api";
import { IndexStatusResponse, Source, SourceStatus, StartIndexingPayload } from "@/types/source";

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

function removeSourceFromIndexStatus(
  current: IndexStatusResponse | undefined,
  sourceId: string
): IndexStatusResponse | undefined {
  if (!current) {
    return current;
  }

  const nextSources = current.sources.filter((source) => source.id !== sourceId);
  const nextBreakdown: Record<string, number> = {};
  for (const source of nextSources) {
    nextBreakdown[source.status] = (nextBreakdown[source.status] ?? 0) + 1;
  }

  const hasActive = hasActiveIndexing(nextBreakdown);

  return {
    ...current,
    total_sources: nextSources.length,
    status_breakdown: nextBreakdown,
    progress: hasActive ? current.progress : null,
    sources: nextSources,
  };
}

function buildOptimisticIndexStatus(
  projectId: string,
  sources: Source[] | undefined,
  current: IndexStatusResponse | undefined
): IndexStatusResponse {
  const optimisticSources =
    sources?.map((source, index) => ({
      id: source.id,
      title: source.title,
      platform: source.platform,
      status: index === 0 ? ("indexing" as const) : source.status,
      last_indexed_at: source.last_indexed_at,
    })) ?? current?.sources ?? [];

  const nextBreakdown: Record<string, number> = {};
  for (const source of optimisticSources) {
    const status = source.status === "ready" || source.status === "failed" ? source.status : "indexing";
    nextBreakdown[status] = (nextBreakdown[status] ?? 0) + 1;
  }

  return {
    project_id: projectId,
    total_sources: optimisticSources.length,
    status_breakdown: nextBreakdown,
    progress: {
      percent: 0,
      overall_percent: 0,
      current_source_title: optimisticSources[0]?.title ?? null,
      current_source_index: optimisticSources.length ? 1 : 0,
      total_sources: optimisticSources.length,
      completed_sources: 0,
      processed_posts: 0,
      total_posts: 0,
      posts_label: "Preparing posts...",
      updated_at: new Date().toISOString(),
      finished_at: null,
    },
    sources: optimisticSources,
  };
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

export function useDeleteSource(projectId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (sourceId: string) => api.deleteSource(sourceId),
    onMutate: async (sourceId) => {
      await queryClient.cancelQueries({ queryKey: ["sources", projectId] });
      await queryClient.cancelQueries({ queryKey: ["index-status", projectId] });
      const previousSources = queryClient.getQueryData<Source[]>(["sources", projectId]);
      const previousIndexStatus = queryClient.getQueryData<IndexStatusResponse>(["index-status", projectId]);
      queryClient.setQueryData<Source[]>(
        ["sources", projectId],
        (current = []) => current.filter((source) => source.id !== sourceId)
      );
      queryClient.setQueryData<IndexStatusResponse | undefined>(["index-status", projectId], (current) =>
        removeSourceFromIndexStatus(current, sourceId)
      );
      return { previousSources, previousIndexStatus };
    },
    onError: (_error, _sourceId, context) => {
      if (context?.previousSources) {
        queryClient.setQueryData(["sources", projectId], context.previousSources);
      }
      if (context?.previousIndexStatus) {
        queryClient.setQueryData(["index-status", projectId], context.previousIndexStatus);
      }
    },
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: ["sources", projectId] });
      queryClient.invalidateQueries({ queryKey: ["projects", projectId] });
      queryClient.invalidateQueries({ queryKey: ["index-status", projectId] });
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
    mutationFn: (payload: StartIndexingPayload) => api.startIndexing(projectId, payload),
    onMutate: async () => {
      await queryClient.cancelQueries({ queryKey: ["index-status", projectId] });
      const previousIndexStatus = queryClient.getQueryData<IndexStatusResponse>(["index-status", projectId]);
      const sources = queryClient.getQueryData<Source[]>(["sources", projectId]);
      queryClient.setQueryData<IndexStatusResponse>(
        ["index-status", projectId],
        buildOptimisticIndexStatus(projectId, sources, previousIndexStatus)
      );
      return { previousIndexStatus };
    },
    onError: (_error, _payload, context) => {
      if (context?.previousIndexStatus) {
        queryClient.setQueryData(["index-status", projectId], context.previousIndexStatus);
      }
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["sources", projectId] });
      queryClient.invalidateQueries({ queryKey: ["projects", projectId] });
      queryClient.invalidateQueries({ queryKey: ["index-status", projectId] });
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
