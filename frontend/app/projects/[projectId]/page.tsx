"use client";

import Link from "next/link";

import { Header } from "@/components/layout/header";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useProject } from "@/hooks/use-projects";

export default function ProjectOverviewPage({ params }: { params: { projectId: string } }) {
  const { data, isLoading, error } = useProject(params.projectId);

  if (isLoading) {
    return <div>Loading...</div>;
  }

  if (!data || error) {
    return <div className="text-rose-700">{error?.message || "Project not found"}</div>;
  }

  return (
    <div className="space-y-8">
      <Header title={data.name} subtitle={data.description || "Project overview"} />

      <div className="grid gap-4 md:grid-cols-3">
        <Metric title="Sources" value={data.stats.total_sources} />
        <Metric title="Posts" value={data.stats.total_posts} />
        <Metric title="Comments" value={data.stats.total_comments} />
      </div>

      <div className="flex flex-wrap gap-3">
        <Button asChild>
          <Link href={`/projects/${params.projectId}/sources`}>Manage sources</Link>
        </Button>
        <Button variant="secondary" asChild>
          <Link href={`/projects/${params.projectId}/analytics`}>Open analytics</Link>
        </Button>
      </div>
    </div>
  );
}

function Metric({ title, value }: { title: string; value: number }) {
  return (
    <Card className="overflow-hidden border-white/10 bg-card/70 backdrop-blur">
      <CardHeader className="pb-4">
        <CardTitle className="text-base text-muted-foreground">{title}</CardTitle>
      </CardHeader>
      <CardContent className="pb-6 text-5xl font-semibold tracking-tight">{value}</CardContent>
    </Card>
  );
}
