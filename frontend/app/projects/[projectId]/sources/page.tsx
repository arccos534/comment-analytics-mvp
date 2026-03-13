"use client";

import { Header } from "@/components/layout/header";
import { IndexingControls } from "@/components/sources/indexing-controls";
import { SourceInputForm } from "@/components/sources/source-input-form";
import { SourceTable } from "@/components/sources/source-table";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useIndexStatus, useSources, useStartIndexing } from "@/hooks/use-sources";

export default function ProjectSourcesPage({ params }: { params: { projectId: string } }) {
  const { data: sources = [], isLoading } = useSources(params.projectId, { poll: true });
  const { data: indexStatus } = useIndexStatus(params.projectId);
  const startIndexing = useStartIndexing(params.projectId);

  return (
    <div className="space-y-8">
      <Header
        title="Sources"
        subtitle="Валидируйте ссылки, сохраняйте источники и запускайте индексацию с нужным охватом."
      />

      <div className="grid gap-5 xl:grid-cols-[1.05fr_0.95fr]">
        <SourceInputForm projectId={params.projectId} />
        <Card className="bg-white/5">
          <CardHeader>
            <CardTitle>Index status</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2 text-sm">
            <div>Total sources: {indexStatus?.total_sources ?? sources.length}</div>
            {indexStatus?.status_breakdown
              ? Object.entries(indexStatus.status_breakdown).map(([status, count]) => (
                  <div key={status} className="flex justify-between rounded-xl bg-muted px-3 py-2">
                    <span>{status}</span>
                    <span>{count as number}</span>
                  </div>
                ))
              : null}
          </CardContent>
        </Card>
      </div>

      <IndexingControls
        disabled={!sources.length}
        isPending={startIndexing.isPending}
        progress={indexStatus?.progress}
        onStart={(payload) => startIndexing.mutate(payload)}
      />

      {isLoading ? <div>Loading sources...</div> : <SourceTable sources={sources} />}
    </div>
  );
}
