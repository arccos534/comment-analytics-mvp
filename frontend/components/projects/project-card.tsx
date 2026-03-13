"use client";

import Link from "next/link";
import { Trash2 } from "lucide-react";

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { useDeleteProject } from "@/hooks/use-projects";
import { formatDate } from "@/lib/utils";
import { Project } from "@/types/project";

export function ProjectCard({ project }: { project: Project }) {
  const deleteProject = useDeleteProject();

  async function handleDelete(event: React.MouseEvent<HTMLButtonElement>) {
    event.preventDefault();
    event.stopPropagation();

    const confirmed = window.confirm(`Delete project "${project.name}"? This action cannot be undone.`);
    if (!confirmed) {
      return;
    }

    try {
      await deleteProject.mutateAsync(project.id);
    } catch (error) {
      const message = error instanceof Error ? error.message : "Failed to delete project";
      window.alert(message);
    }
  }

  return (
    <Card className="relative h-full bg-white/5 transition hover:-translate-y-1 hover:bg-white/[0.07]">
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
        <CardHeader className="pr-16">
          <CardTitle>{project.name}</CardTitle>
          <CardDescription>{project.description || "No description"}</CardDescription>
        </CardHeader>
        <CardContent className="text-sm text-muted-foreground">
          Created {formatDate(project.created_at)}
        </CardContent>
      </Link>
    </Card>
  );
}
