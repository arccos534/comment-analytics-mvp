"use client";

import Link from "next/link";
import { useMemo, useState } from "react";
import { ChevronDown, ChevronRight, Database, FileText } from "lucide-react";

import { useReportsTree } from "@/hooks/use-analysis";
import { useProjects } from "@/hooks/use-projects";

export function Sidebar() {
  const projectsQuery = useProjects();
  const reportsTreeQuery = useReportsTree();
  const [openProjects, setOpenProjects] = useState<Record<string, boolean>>({});

  const reportMap = useMemo(
    () => new Map((reportsTreeQuery.data ?? []).map((item) => [item.project_id, item.reports])),
    [reportsTreeQuery.data]
  );

  const toggleProject = (projectId: string) => {
    setOpenProjects((current) => ({ ...current, [projectId]: !current[projectId] }));
  };

  return (
    <aside className="hidden min-h-screen flex-col p-5 xl:flex">
      <div className="app-panel-strong flex h-full flex-col overflow-hidden px-6 py-7">
        <div>
          <p className="section-kicker">Comment Analytics</p>
          <h1 className="mt-4 inline-flex flex-wrap items-baseline gap-3 text-[36px] font-semibold tracking-[-0.06em] text-foreground">
            <span>Dashboard</span>
            <span className="section-kicker text-[13px]">By arccos</span>
          </h1>
        </div>

        <nav className="mt-10 space-y-3">
          <Link
            className="group flex items-center gap-3 rounded-[22px] border border-white/10 bg-white/[0.035] px-4 py-3.5 text-sm font-medium text-foreground transition hover:border-cyan-300/20 hover:bg-white/[0.06]"
            href="/projects"
          >
            <span className="rounded-xl bg-cyan-400/10 p-2 text-cyan-200 transition group-hover:bg-cyan-400/15">
              <Database className="h-4 w-4" />
            </span>
            Projects
          </Link>

          <div className="rounded-[22px] border border-white/10 bg-white/[0.03] px-4 py-4">
            <div className="flex items-center gap-3">
              <span className="rounded-xl bg-cyan-400/10 p-2 text-cyan-200">
                <FileText className="h-4 w-4" />
              </span>
              <div>
                <div className="text-sm font-medium text-foreground">Reports</div>
                <div className="text-xs text-muted-foreground">Saved reports by project</div>
              </div>
            </div>

            <div className="mt-4 space-y-2">
              {(projectsQuery.data ?? []).map((project) => {
                const reports = reportMap.get(project.id) ?? [];
                const isOpen = openProjects[project.id] ?? false;

                return (
                  <div key={project.id} className="rounded-2xl border border-white/8 bg-white/[0.025]">
                    <button
                      type="button"
                      onClick={() => toggleProject(project.id)}
                      className="flex w-full items-center justify-between gap-3 px-3 py-3 text-left transition hover:bg-white/[0.04]"
                    >
                      <div className="min-w-0">
                        <div className="truncate text-sm font-medium text-foreground">{project.name}</div>
                        <div className="text-xs text-muted-foreground">{reports.length} reports</div>
                      </div>
                      {isOpen ? (
                        <ChevronDown className="h-4 w-4 shrink-0 text-muted-foreground" />
                      ) : (
                        <ChevronRight className="h-4 w-4 shrink-0 text-muted-foreground" />
                      )}
                    </button>

                    {isOpen ? (
                      <div className="border-t border-white/8 px-2 py-2">
                        {reports.length ? (
                          <div className="space-y-1">
                            {reports.map((report) => (
                              <Link
                                key={report.analysis_run_id}
                                href={`/projects/${project.id}/reports/${report.analysis_run_id}`}
                                className="block rounded-xl px-3 py-2 text-sm text-muted-foreground transition hover:bg-white/[0.05] hover:text-foreground"
                              >
                                <div className="line-clamp-2">{report.title}</div>
                              </Link>
                            ))}
                          </div>
                        ) : (
                          <div className="px-3 py-2 text-xs text-muted-foreground">No reports yet</div>
                        )}
                      </div>
                    ) : null}
                  </div>
                );
              })}
            </div>
          </div>
        </nav>
      </div>
    </aside>
  );
}
