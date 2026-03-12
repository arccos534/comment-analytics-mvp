import Link from "next/link";

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { formatDate } from "@/lib/utils";
import { Project } from "@/types/project";

export function ProjectCard({ project }: { project: Project }) {
  return (
    <Link href={`/projects/${project.id}`}>
      <Card className="h-full bg-white/80 transition hover:-translate-y-1 hover:bg-white">
        <CardHeader>
          <CardTitle>{project.name}</CardTitle>
          <CardDescription>{project.description || "Без описания"}</CardDescription>
        </CardHeader>
        <CardContent className="text-sm text-muted-foreground">
          Создан {formatDate(project.created_at)}
        </CardContent>
      </Card>
    </Link>
  );
}
