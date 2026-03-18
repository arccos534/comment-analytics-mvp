"use client";

import { AnalysisCreatePayload } from "@/types/analytics";

type StoredAnalysisDraft = {
  promptText: string;
  theme: string;
  keywords: string;
  analysisMode: string;
  periodFrom: string;
  periodTo: string;
  platforms: string[];
  selectedSourceIds: string[];
};

type StoredActiveRun = {
  runId: string;
};

function isBrowser() {
  return typeof window !== "undefined";
}

function draftKey(projectId: string) {
  return `comment-analytics:analysis-draft:${projectId}`;
}

function pendingKey(projectId: string) {
  return `comment-analytics:analysis-pending:${projectId}`;
}

function activeRunKey(projectId: string) {
  return `comment-analytics:analysis-active-run:${projectId}`;
}

function safeParse<T>(raw: string | null): T | null {
  if (!raw) {
    return null;
  }
  try {
    return JSON.parse(raw) as T;
  } catch {
    return null;
  }
}

export function loadAnalysisDraft(projectId: string): StoredAnalysisDraft | null {
  if (!isBrowser()) {
    return null;
  }
  return safeParse<StoredAnalysisDraft>(window.sessionStorage.getItem(draftKey(projectId)));
}

export function saveAnalysisDraft(projectId: string, draft: StoredAnalysisDraft) {
  if (!isBrowser()) {
    return;
  }
  window.sessionStorage.setItem(draftKey(projectId), JSON.stringify(draft));
}

export function loadPendingAnalysisRequest(projectId: string): AnalysisCreatePayload | null {
  if (!isBrowser()) {
    return null;
  }
  return safeParse<AnalysisCreatePayload>(window.sessionStorage.getItem(pendingKey(projectId)));
}

export function savePendingAnalysisRequest(projectId: string, payload: AnalysisCreatePayload) {
  if (!isBrowser()) {
    return;
  }
  window.sessionStorage.setItem(pendingKey(projectId), JSON.stringify(payload));
}

export function clearPendingAnalysisRequest(projectId: string) {
  if (!isBrowser()) {
    return;
  }
  window.sessionStorage.removeItem(pendingKey(projectId));
}

export function loadActiveAnalysisRun(projectId: string): StoredActiveRun | null {
  if (!isBrowser()) {
    return null;
  }
  return safeParse<StoredActiveRun>(window.sessionStorage.getItem(activeRunKey(projectId)));
}

export function saveActiveAnalysisRun(projectId: string, runId: string) {
  if (!isBrowser()) {
    return;
  }
  window.sessionStorage.setItem(activeRunKey(projectId), JSON.stringify({ runId }));
}

export function clearActiveAnalysisRun(projectId: string) {
  if (!isBrowser()) {
    return;
  }
  window.sessionStorage.removeItem(activeRunKey(projectId));
}
