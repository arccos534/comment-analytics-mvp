"use client";

import { Header } from "@/components/layout/header";
import { SourceInputForm } from "@/components/sources/source-input-form";
import { SourceTable } from "@/components/sources/source-table";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useIndexStatus, useSources, useStartIndexing } from "@/hooks/use-sources";

export default function ProjectSourcesPage({ params }: { params: { projectId: string } }) {
  const { data: sources = [], isLoading } = useSources(params.projectId, { poll: true });
  const { data: indexStatus } = useIndexStatus(params.projectId);
  const startIndexing = useStartIndexing(params.projectId);

  return (
    <div className="space-y-8">
      <div className="flex flex-col gap-4 md:flex-row md:items-end md:justify-between">
        <Header title="Sources" subtitle="Валидируйте ссылки, сохраняйте источники и запускайте индексацию." />
        <Button onClick={() => startIndexing.mutate()} disabled={startIndexing.isPending || !sources.length}>
          {startIndexing.isPending ? "Indexing..." : "Start indexing"}
        </Button>
      </div>

      <div className="grid gap-5 xl:grid-cols-[1.05fr_0.95fr]">
        <SourceInputForm projectId={params.projectId} />
        <Card className="bg-white/80">
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

      {isLoading ? <div>Loading sources...</div> : <SourceTable sources={sources} />}
    </div>
  );
}
