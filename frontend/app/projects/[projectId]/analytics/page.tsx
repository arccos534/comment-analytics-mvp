"use client";

import Link from "next/link";

import { AnalyticsForm } from "@/components/analytics/analytics-form";
import { Header } from "@/components/layout/header";
import { Button } from "@/components/ui/button";
import { useSources } from "@/hooks/use-sources";
import { useUiStore } from "@/store/ui-store";

export default function ProjectAnalyticsPage({ params }: { params: { projectId: string } }) {
  const { data: sources = [] } = useSources(params.projectId);
  const latestAnalysisRunId = useUiStore((state) => state.latestAnalysisRunId);

  return (
    <div className="space-y-8">
      <div className="flex flex-col gap-4 md:flex-row md:items-end md:justify-between">
        <Header title="Analytics" subtitle="Формируйте тематические отчеты по комментариям и сигналам аудитории." />
        {latestAnalysisRunId ? (
          <Button variant="secondary" asChild>
            <Link href={`/projects/${params.projectId}/reports/${latestAnalysisRunId}`}>Open latest report</Link>
          </Button>
        ) : null}
      </div>
      <AnalyticsForm projectId={params.projectId} sources={sources} />
    </div>
  );
}
