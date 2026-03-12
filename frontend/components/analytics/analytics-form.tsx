"use client";

import { useMemo, useState } from "react";
import { useRouter } from "next/navigation";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Checkbox } from "@/components/ui/checkbox";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useRunAnalysis } from "@/hooks/use-analysis";
import { useUiStore } from "@/store/ui-store";
import { Source } from "@/types/source";

export function AnalyticsForm({ projectId, sources }: { projectId: string; sources: Source[] }) {
  const router = useRouter();
  const runAnalysis = useRunAnalysis(projectId);
  const setLatestAnalysisRunId = useUiStore((state) => state.setLatestAnalysisRunId);

  const [promptText, setPromptText] = useState("Проанализируй реакцию аудитории на продукт, цену и качество сервиса.");
  const [theme, setTheme] = useState("Продукт и пользовательский опыт");
  const [keywords, setKeywords] = useState("цена, качество, поддержка, доставка");
  const [periodFrom, setPeriodFrom] = useState("");
  const [periodTo, setPeriodTo] = useState("");
  const [platforms, setPlatforms] = useState<string[]>(["telegram", "vk"]);
  const [selectedSourceIds, setSelectedSourceIds] = useState<string[]>([]);

  const readySources = useMemo(() => sources.filter((source) => source.status === "ready"), [sources]);

  async function handleSubmit() {
    const run = await runAnalysis.mutateAsync({
      prompt_text: promptText,
      theme,
      keywords: keywords.split(",").map((value) => value.trim()).filter(Boolean),
      period_from: periodFrom ? new Date(periodFrom).toISOString() : null,
      period_to: periodTo ? new Date(periodTo).toISOString() : null,
      platforms: platforms as ("telegram" | "vk")[],
      source_ids: selectedSourceIds
    });
    setLatestAnalysisRunId(run.id);
    router.push(`/projects/${projectId}/reports/${run.id}`);
  }

  function togglePlatform(platform: string) {
    setPlatforms((current) => (current.includes(platform) ? current.filter((item) => item !== platform) : [...current, platform]));
  }

  function toggleSource(sourceId: string) {
    setSelectedSourceIds((current) =>
      current.includes(sourceId) ? current.filter((item) => item !== sourceId) : [...current, sourceId]
    );
  }

  return (
    <Card className="bg-white/80">
      <CardHeader>
        <CardTitle>Generate report</CardTitle>
        <CardDescription>Настройте тему, фильтры и период анализа.</CardDescription>
      </CardHeader>
      <CardContent className="grid gap-6 lg:grid-cols-2">
        <div className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="prompt">Prompt</Label>
            <Input id="prompt" value={promptText} onChange={(event) => setPromptText(event.target.value)} />
          </div>
          <div className="space-y-2">
            <Label htmlFor="theme">Theme</Label>
            <Input id="theme" value={theme} onChange={(event) => setTheme(event.target.value)} />
          </div>
          <div className="space-y-2">
            <Label htmlFor="keywords">Keywords</Label>
            <Input id="keywords" value={keywords} onChange={(event) => setKeywords(event.target.value)} />
          </div>
          <div className="grid gap-4 sm:grid-cols-2">
            <div className="space-y-2">
              <Label htmlFor="period-from">From</Label>
              <Input id="period-from" type="date" value={periodFrom} onChange={(event) => setPeriodFrom(event.target.value)} />
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
            <Label>Sources</Label>
            <div className="max-h-60 space-y-2 overflow-auto rounded-2xl bg-muted p-3">
              {readySources.length ? (
                readySources.map((source) => (
                  <label key={source.id} className="flex items-start gap-3 rounded-xl bg-white px-3 py-2 text-sm">
                    <Checkbox checked={selectedSourceIds.includes(source.id)} onCheckedChange={() => toggleSource(source.id)} />
                    <span>{source.title || source.source_url}</span>
                  </label>
                ))
              ) : (
                <div className="text-sm text-muted-foreground">Сначала проиндексируйте хотя бы один источник.</div>
              )}
            </div>
          </div>
          <Button onClick={handleSubmit} disabled={runAnalysis.isPending || !promptText.trim()}>
            {runAnalysis.isPending ? "Generating..." : "Generate report"}
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}
