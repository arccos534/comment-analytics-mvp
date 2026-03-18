"use client";

import { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Checkbox } from "@/components/ui/checkbox";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select } from "@/components/ui/select";
import { useRunAnalysis } from "@/hooks/use-analysis";
import {
  clearPendingAnalysisRequest,
  loadActiveAnalysisRun,
  loadAnalysisDraft,
  loadPendingAnalysisRequest,
  saveActiveAnalysisRun,
  saveAnalysisDraft,
  savePendingAnalysisRequest,
} from "@/lib/analysis-run-storage";
import { api } from "@/lib/api";
import { useUiStore } from "@/store/ui-store";
import { AnalysisCreatePayload, AnalysisMode } from "@/types/analytics";
import { Source } from "@/types/source";

const ANALYSIS_MODE_OPTIONS: Array<{ value: AnalysisMode | "auto"; label: string }> = [
  { value: "auto", label: "Авто" },
  { value: "source_comparison", label: "Сравнение источников" },
  { value: "post_popularity", label: "Популярные посты" },
  { value: "post_underperformance", label: "Слабые посты" },
  { value: "post_sentiment", label: "Реакция на посты" },
  { value: "theme_sentiment", label: "Темы и тональность" },
  { value: "theme_interest", label: "Темы и интерес аудитории" },
  { value: "theme_popularity", label: "Популярные темы" },
  { value: "theme_underperformance", label: "Непопулярные темы" },
  { value: "topic_report", label: "Тематический отчет" },
  { value: "mixed", label: "Смешанный режим" },
];

export function AnalyticsForm({ projectId, sources }: { projectId: string; sources: Source[] }) {
  const router = useRouter();
  const runAnalysis = useRunAnalysis(projectId);
  const setLatestAnalysisRunId = useUiStore((state) => state.setLatestAnalysisRunId);

  const [promptText, setPromptText] = useState("");
  const [theme, setTheme] = useState("");
  const [keywords, setKeywords] = useState("");
  const [analysisMode, setAnalysisMode] = useState<AnalysisMode | "auto">("auto");
  const [periodFrom, setPeriodFrom] = useState("");
  const [periodTo, setPeriodTo] = useState("");
  const [platforms, setPlatforms] = useState<string[]>(["telegram", "vk"]);
  const [selectedSourceIds, setSelectedSourceIds] = useState<string[]>([]);
  const [isRestoringRun, setIsRestoringRun] = useState(true);
  const [isDraftLoaded, setIsDraftLoaded] = useState(false);

  const readySources = useMemo(() => sources.filter((source) => source.status === "ready"), [sources]);
  const allSourcesSelected =
    readySources.length > 0 && readySources.every((source) => selectedSourceIds.includes(source.id));

  useEffect(() => {
    const draft = loadAnalysisDraft(projectId);
    if (draft) {
      setPromptText(draft.promptText || "");
      setTheme(draft.theme || "");
      setKeywords(draft.keywords || "");
      setAnalysisMode((draft.analysisMode as AnalysisMode | "auto") || "auto");
      setPeriodFrom(draft.periodFrom || "");
      setPeriodTo(draft.periodTo || "");
      setPlatforms(draft.platforms?.length ? draft.platforms : ["telegram", "vk"]);
      setSelectedSourceIds(draft.selectedSourceIds || []);
    }
    setIsDraftLoaded(true);
  }, [projectId]);

  useEffect(() => {
    if (!isDraftLoaded) {
      return;
    }
    saveAnalysisDraft(projectId, {
      promptText,
      theme,
      keywords,
      analysisMode,
      periodFrom,
      periodTo,
      platforms,
      selectedSourceIds,
    });
  }, [analysisMode, isDraftLoaded, keywords, periodFrom, periodTo, platforms, projectId, promptText, selectedSourceIds, theme]);

  useEffect(() => {
    let cancelled = false;
    const activeRun = loadActiveAnalysisRun(projectId);
    if (activeRun?.runId) {
      setLatestAnalysisRunId(activeRun.runId);
      router.replace(`/projects/${projectId}/reports/${activeRun.runId}`);
      return;
    }

    const pendingRequest = loadPendingAnalysisRequest(projectId);
    if (!pendingRequest) {
      setIsRestoringRun(false);
      return;
    }

    let attempts = 0;
    const maxAttempts = 10;

    const resolvePendingRun = async () => {
      attempts += 1;
      try {
        const run = await api.findActiveAnalysisRun(projectId, pendingRequest);
        if (cancelled) {
          return;
        }
        if (run?.id) {
          clearPendingAnalysisRequest(projectId);
          saveActiveAnalysisRun(projectId, run.id);
          setLatestAnalysisRunId(run.id);
          router.replace(`/projects/${projectId}/reports/${run.id}`);
          return;
        }
      } catch {
        if (cancelled) {
          return;
        }
      }

      if (attempts >= maxAttempts) {
        clearPendingAnalysisRequest(projectId);
        setIsRestoringRun(false);
        return;
      }

      window.setTimeout(resolvePendingRun, 1500);
    };

    void resolvePendingRun();

    return () => {
      cancelled = true;
    };
  }, [projectId, router, setLatestAnalysisRunId]);

  function buildPayload(): AnalysisCreatePayload {
    return {
      prompt_text: promptText,
      theme,
      keywords: keywords
        .split(",")
        .map((value) => value.trim())
        .filter(Boolean),
      analysis_mode_override: analysisMode === "auto" ? null : analysisMode,
      period_from: periodFrom ? new Date(periodFrom).toISOString() : null,
      period_to: periodTo ? new Date(periodTo).toISOString() : null,
      platforms: platforms as ("telegram" | "vk")[],
      source_ids: selectedSourceIds,
    };
  }

  async function handleSubmit() {
    const payload = buildPayload();
    savePendingAnalysisRequest(projectId, payload);
    const run = await runAnalysis.mutateAsync(payload);
    clearPendingAnalysisRequest(projectId);
    saveActiveAnalysisRun(projectId, run.id);
    setLatestAnalysisRunId(run.id);
    router.push(`/projects/${projectId}/reports/${run.id}`);
  }

  function togglePlatform(platform: string) {
    setPlatforms((current) =>
      current.includes(platform) ? current.filter((item) => item !== platform) : [...current, platform]
    );
  }

  function toggleSource(sourceId: string) {
    setSelectedSourceIds((current) =>
      current.includes(sourceId) ? current.filter((item) => item !== sourceId) : [...current, sourceId]
    );
  }

  function toggleAllSources() {
    setSelectedSourceIds(allSourcesSelected ? [] : readySources.map((source) => source.id));
  }

  return (
    <Card className="bg-white/5">
      <CardHeader>
        <CardTitle>Generate report</CardTitle>
        <CardDescription>
          Тема и keywords относятся к постам и новостям. Prompt задает фокус анализа комментариев и источников.
        </CardDescription>
      </CardHeader>
      <CardContent className="grid gap-6 lg:grid-cols-2">
        <div className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="theme">Theme of posts/news</Label>
            <Input
              id="theme"
              value={theme}
              onChange={(event) => setTheme(event.target.value)}
              placeholder="Например: благоустройство города, дворы, дороги"
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="keywords">Keywords in posts/news</Label>
            <Input
              id="keywords"
              value={keywords}
              onChange={(event) => setKeywords(event.target.value)}
              placeholder="Например: парковка, тротуары, освещение"
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="prompt">Prompt for source and comment analysis</Label>
            <Input
              id="prompt"
              value={promptText}
              onChange={(event) => setPromptText(event.target.value)}
              placeholder="Например: сравни активность источников и реакцию аудитории на их новости"
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="analysis-mode">Режим анализа</Label>
            <Select
              id="analysis-mode"
              value={analysisMode}
              onChange={(event) => setAnalysisMode(event.target.value as AnalysisMode | "auto")}
            >
              {ANALYSIS_MODE_OPTIONS.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </Select>
            <div className="text-xs text-muted-foreground">
              Авто сам определяет режим по prompt. Ручной выбор задает основной вектор анализа, а prompt уточняет тему,
              период и формат ответа.
            </div>
          </div>
          <div className="grid gap-4 sm:grid-cols-2">
            <div className="space-y-2">
              <Label htmlFor="period-from">From</Label>
              <Input
                id="period-from"
                type="date"
                value={periodFrom}
                onChange={(event) => setPeriodFrom(event.target.value)}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="period-to">To</Label>
              <Input id="period-to" type="date" value={periodTo} onChange={(event) => setPeriodTo(event.target.value)} />
            </div>
          </div>
        </div>
        <div className="space-y-5">
          <div className="space-y-3">
            <Label>Platforms</Label>
            <div className="grid gap-2">
              {["telegram", "vk"].map((platform) => (
                <label key={platform} className="flex items-center gap-3 rounded-xl bg-muted px-3 py-2 text-sm">
                  <Checkbox checked={platforms.includes(platform)} onCheckedChange={() => togglePlatform(platform)} />
                  <span className="capitalize">{platform}</span>
                </label>
              ))}
            </div>
          </div>
          <div className="space-y-3">
            <div className="flex items-center justify-between gap-3">
              <Label>Sources</Label>
              <Button
                variant="ghost"
                size="sm"
                className="h-7 px-2 text-xs"
                onClick={toggleAllSources}
                disabled={!readySources.length}
              >
                {allSourcesSelected ? "Clear all" : "Select all"}
              </Button>
            </div>
            <div className="max-h-60 space-y-2 overflow-auto rounded-2xl bg-muted p-3">
              {readySources.length ? (
                readySources.map((source) => (
                  <label key={source.id} className="flex items-start gap-3 rounded-xl bg-white/5 px-3 py-2 text-sm">
                    <Checkbox
                      checked={selectedSourceIds.includes(source.id)}
                      onCheckedChange={() => toggleSource(source.id)}
                    />
                    <span>{source.title || source.source_url}</span>
                  </label>
                ))
              ) : (
                <div className="text-sm text-muted-foreground">Сначала проиндексируйте хотя бы один источник.</div>
              )}
            </div>
          </div>
          <Button onClick={handleSubmit} disabled={runAnalysis.isPending || isRestoringRun || !promptText.trim()}>
            {isRestoringRun ? "Restoring..." : runAnalysis.isPending ? "Generating..." : "Generate report"}
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}
