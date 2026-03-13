"use client";

import { Header } from "@/components/layout/header";
import { CreateProjectDialog } from "@/components/projects/create-project-dialog";
import { ProjectCard } from "@/components/projects/project-card";
import { Card, CardContent } from "@/components/ui/card";
import { useProjects } from "@/hooks/use-projects";

export default function ProjectsPage() {
  const { data, isLoading, error } = useProjects();

  return (
    <div className="space-y-8">
      <div className="flex flex-col gap-4 md:flex-row md:items-end md:justify-between">
        <Header
          title="Projects"
          subtitle="Создавайте базы источников, запускайте индексацию и собирайте отчеты по реакции аудитории в одном интерфейсе."
        />
        <CreateProjectDialog />
      </div>

      {isLoading ? (
        <Card className="app-panel">
          <CardContent className="p-6 text-slate-300/70">Загружаем проекты...</CardContent>
        </Card>
      ) : null}

      {error ? (
        <Card className="app-panel border-rose-400/15">
          <CardContent className="p-6 text-rose-300">{error.message}</CardContent>
        </Card>
      ) : null}

      <div className="grid gap-5 md:grid-cols-2 xl:grid-cols-3">
        {data?.map((project) => (
          <ProjectCard key={project.id} project={project} />
        ))}
      </div>
    </div>
  );
}
