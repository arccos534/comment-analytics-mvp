"use client";

import Link from "next/link";
import { ArrowUpRight, FolderKanban, Trash2 } from "lucide-react";

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { useDeleteProject } from "@/hooks/use-projects";
import { formatDate } from "@/lib/utils";
import { Project } from "@/types/project";

export function ProjectCard({ project }: { project: Project }) {
  const deleteProject = useDeleteProject();

  async function handleDelete(event: React.MouseEvent<HTMLButtonElement>) {
    event.preventDefault();
    event.stopPropagation();

    const confirmed = window.confirm(`Удалить проект "${project.name}"? Это действие нельзя отменить.`);
    if (!confirmed) {
      return;
    }

    try {
      await deleteProject.mutateAsync(project.id);
    } catch (error) {
      const message = error instanceof Error ? error.message : "Не удалось удалить проект";
      window.alert(message);
    }
  }

  return (
    <Card className="group relative h-full overflow-hidden border-white/10 bg-[linear-gradient(180deg,rgba(255,255,255,0.06),rgba(255,255,255,0.025))] transition duration-300 hover:-translate-y-1.5 hover:border-cyan-300/20 hover:shadow-[0_24px_60px_rgba(0,0,0,0.32)]">
      <div className="pointer-events-none absolute inset-x-0 top-0 h-24 bg-[radial-gradient(circle_at_top_left,rgba(84,194,239,0.16),transparent_60%)] opacity-80" />
      <button
        type="button"
        aria-label={`Delete ${project.name}`}
        className="absolute right-4 top-4 z-10 rounded-lg border border-rose-500/20 bg-rose-500/10 p-2 text-rose-300 transition hover:bg-rose-500/20 disabled:opacity-50"
        disabled={deleteProject.isPending}
        onClick={handleDelete}
      >
        <Trash2 className="h-4 w-4" />
      </button>

      <Link className="block h-full" href={`/projects/${project.id}`}>
        <CardHeader className="relative pr-16">
          <div className="mb-5 flex items-center justify-between">
            <div className="inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/[0.04] px-3 py-1.5 text-xs text-slate-300/72">
              <FolderKanban className="h-3.5 w-3.5 text-cyan-200" />
              Project workspace
            </div>
            <ArrowUpRight className="h-4 w-4 text-slate-400 transition group-hover:text-cyan-200" />
          </div>
          <CardTitle className="text-[22px] tracking-[-0.03em]">{project.name}</CardTitle>
          <CardDescription className="mt-2 min-h-[44px] text-slate-300/68">
            {project.description || "База для источников, индексации и аналитических отчетов."}
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4 text-sm text-muted-foreground">
          <div className="h-px w-full bg-white/10" />
          <div className="flex items-center justify-between gap-4">
            <span className="text-slate-400">Создан</span>
            <span className="text-slate-200">{formatDate(project.created_at)}</span>
          </div>
        </CardContent>
      </Link>
    </Card>
  );
}
