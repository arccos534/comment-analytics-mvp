"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";

import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { useCreateProject } from "@/hooks/use-projects";

export function CreateProjectDialog() {
  const router = useRouter();
  const createProject = useCreateProject();
  const [open, setOpen] = useState(false);
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");

  async function handleSubmit() {
    const project = await createProject.mutateAsync({ name, description });
    setOpen(false);
    setName("");
    setDescription("");
    router.push(`/projects/${project.id}`);
  }

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button size="lg">Create database</Button>
      </DialogTrigger>
      <DialogContent className="border-white/10 bg-[linear-gradient(180deg,rgba(18,24,34,0.98),rgba(13,19,28,0.98))]">
        <DialogHeader>
          <DialogTitle>Новая база данных</DialogTitle>
          <DialogDescription>Создайте рабочую базу для источников Telegram и VK.</DialogDescription>
        </DialogHeader>
        <div className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="project-name">Название</Label>
            <Input id="project-name" value={name} onChange={(event) => setName(event.target.value)} />
          </div>
          <div className="space-y-2">
            <Label htmlFor="project-description">Описание</Label>
            <Textarea
              id="project-description"
              value={description}
              onChange={(event) => setDescription(event.target.value)}
              className="min-h-[100px]"
            />
          </div>
          <Button disabled={!name.trim() || createProject.isPending} onClick={handleSubmit} className="w-full">
            {createProject.isPending ? "Создаем..." : "Создать"}
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}
