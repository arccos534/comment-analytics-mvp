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
    return <div className="text-rose-300">{error?.message || "Project not found"}</div>;
  }

  return (
    <div className="space-y-8">
      <Header title={data.name} subtitle={data.description || "Обзор проекта, источников и текущего объема данных."} />

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
    <Card className="overflow-hidden border-white/10 bg-[linear-gradient(180deg,rgba(255,255,255,0.06),rgba(255,255,255,0.025))]">
      <CardHeader className="pb-4">
        <CardTitle className="text-base text-slate-300/68">{title}</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4 pb-6">
        <div className="text-5xl font-semibold tracking-[-0.05em] text-white">{value}</div>
        <div className="h-1.5 w-24 rounded-full bg-[linear-gradient(90deg,rgba(84,194,239,0.95),rgba(84,194,239,0.15))]" />
      </CardContent>
    </Card>
  );
}
