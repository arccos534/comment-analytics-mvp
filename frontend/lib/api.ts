import { AnalysisCreatePayload, AnalysisRun, ReportSnapshot } from "@/types/analytics";
import { Project, ProjectDetail } from "@/types/project";
import { IndexStatusResponse, Source, SourceBulkCreateResponse, SourceValidationResult, StartIndexingPayload } from "@/types/source";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000/api/v1";

async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers ?? {})
    }
  });

  if (!response.ok) {
    const payload = await response.json().catch(() => ({ detail: "Request failed" }));
    throw new Error(payload.detail ?? "Request failed");
  }

  if (response.status === 204) {
    return undefined as T;
  }

  return response.json();
}

export const api = {
  listProjects: () => apiFetch<Project[]>("/projects"),
  createProject: (payload: { name: string; description?: string }) =>
    apiFetch<Project>("/projects", { method: "POST", body: JSON.stringify(payload) }),
  deleteProject: (projectId: string) => apiFetch<void>(`/projects/${projectId}`, { method: "DELETE" }),
  getProject: (projectId: string) => apiFetch<ProjectDetail>(`/projects/${projectId}`),
  listSources: (projectId: string) => apiFetch<Source[]>(`/projects/${projectId}/sources`),
  validateSources: (urls: string[]) =>
    apiFetch<SourceValidationResult[]>("/sources/validate", { method: "POST", body: JSON.stringify({ urls }) }),
  addSources: (projectId: string, urls: string[]) =>
    apiFetch<SourceBulkCreateResponse>(`/projects/${projectId}/sources`, {
      method: "POST",
      body: JSON.stringify({ urls })
    }),
  startIndexing: (projectId: string, payload: StartIndexingPayload) =>
    apiFetch<{ status: string; task_id: string }>(`/projects/${projectId}/index`, {
      method: "POST",
      body: JSON.stringify(payload)
    }),
  getIndexStatus: (projectId: string) => apiFetch<IndexStatusResponse>(`/projects/${projectId}/index-status`),
  runAnalysis: (projectId: string, payload: AnalysisCreatePayload) =>
    apiFetch<AnalysisRun>(`/projects/${projectId}/analyze`, {
      method: "POST",
      body: JSON.stringify(payload)
    }),
  getAnalysisRun: (analysisRunId: string) => apiFetch<AnalysisRun>(`/analysis-runs/${analysisRunId}`),
  getReport: (analysisRunId: string) => apiFetch<ReportSnapshot>(`/analysis-runs/${analysisRunId}/report`)
};
