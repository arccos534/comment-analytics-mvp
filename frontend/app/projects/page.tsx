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
          subtitle="Создавайте проекты, индексируйте Telegram/VK и запускайте аналитические отчеты."
        />
        <CreateProjectDialog />
      </div>

      {isLoading ? <Card><CardContent className="p-6">Loading projects...</CardContent></Card> : null}
      {error ? <Card><CardContent className="p-6 text-rose-700">{error.message}</CardContent></Card> : null}

      <div className="grid gap-5 md:grid-cols-2 xl:grid-cols-3">
        {data?.map((project) => <ProjectCard key={project.id} project={project} />)}
      </div>
    </div>
  );
}
