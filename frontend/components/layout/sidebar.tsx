"use client";

import Link from "next/link";
import { type MouseEvent, useMemo, useState } from "react";
import { usePathname, useRouter } from "next/navigation";
import { ChevronDown, ChevronRight, Database, FileText, Trash2 } from "lucide-react";

import { useDeleteReport, useReportsTree } from "@/hooks/use-analysis";
import { useProjects } from "@/hooks/use-projects";
import { cn, formatReportGroupDate } from "@/lib/utils";

export function Sidebar() {
  const pathname = usePathname();
  const router = useRouter();
  const projectsQuery = useProjects();
  const reportsTreeQuery = useReportsTree();
  const deleteReport = useDeleteReport();
  const [openReports, setOpenReports] = useState(pathname.includes("/reports/"));
  const [openProjects, setOpenProjects] = useState<Record<string, boolean>>({});

  const reportMap = useMemo(
    () => new Map((reportsTreeQuery.data ?? []).map((item) => [item.project_id, item.reports])),
    [reportsTreeQuery.data]
  );

  const toggleProject = (projectId: string) => {
    setOpenProjects((current) => ({ ...current, [projectId]: !current[projectId] }));
  };

  const handleDeleteReport = async (
    event: MouseEvent<HTMLButtonElement>,
    projectId: string,
    analysisRunId: string,
    title: string
  ) => {
    event.preventDefault();
    event.stopPropagation();

    const confirmed = window.confirm(`Delete report "${title}"?`);
    if (!confirmed) {
      return;
    }

    try {
      await deleteReport.mutateAsync(analysisRunId);
      if (pathname === `/projects/${projectId}/reports/${analysisRunId}`) {
        router.push(`/projects/${projectId}/analytics`);
      }
    } catch (error) {
      const message = error instanceof Error ? error.message : "Failed to delete report";
      window.alert(message);
    }
  };

  return (
    <aside className="hidden min-h-screen flex-col p-5 xl:flex">
      <div className="app-panel-strong flex h-full flex-col overflow-hidden px-6 py-7">
        <div>
          <p className="section-kicker">Comment Analytics</p>
          <h1 className="mt-4 inline-flex items-baseline gap-3 whitespace-nowrap text-[36px] font-semibold tracking-[-0.06em] text-foreground">
            <span>Dashboard</span>
            <span className="section-kicker text-[13px]">by arccos</span>
          </h1>
        </div>

        <nav className="mt-10 space-y-3">
          <Link
            className={cn(
              "group flex items-center gap-3 rounded-[22px] border px-4 py-3.5 text-sm font-medium transition",
              pathname === "/projects"
                ? "border-cyan-300/25 bg-cyan-400/[0.08] text-foreground shadow-[0_0_0_1px_rgba(92,217,255,0.06)]"
                : "border-white/10 bg-white/[0.035] text-foreground hover:border-cyan-300/20 hover:bg-white/[0.06]"
            )}
            href="/projects"
          >
            <span className="rounded-xl bg-cyan-400/10 p-2 text-cyan-200 transition group-hover:bg-cyan-400/15">
              <Database className="h-4 w-4" />
            </span>
            Projects
          </Link>

          <div className="rounded-[22px] border border-white/10 bg-white/[0.03] px-4 py-4">
            <button
              type="button"
              onClick={() => setOpenReports((value) => !value)}
              className="flex w-full items-center justify-between gap-3 text-left"
            >
              <div className="flex items-center gap-3">
                <span className="rounded-xl bg-cyan-400/10 p-2 text-cyan-200">
                  <FileText className="h-4 w-4" />
                </span>
                <div>
                  <div className="text-sm font-medium text-foreground">Reports</div>
                  <div className="text-xs text-muted-foreground">Saved reports by project</div>
                </div>
              </div>
              {openReports ? (
                <ChevronDown className="h-4 w-4 shrink-0 text-muted-foreground" />
              ) : (
                <ChevronRight className="h-4 w-4 shrink-0 text-muted-foreground" />
              )}
            </button>

            {openReports ? (
              <div className="mt-4 space-y-2">
                {(projectsQuery.data ?? []).map((project) => {
                  const reports = reportMap.get(project.id) ?? [];
                  const hasActiveReport = pathname.startsWith(`/projects/${project.id}/reports/`);
                  const isOpen = openProjects[project.id] ?? hasActiveReport;
                  const groupedReports = reports.reduce<Record<string, typeof reports>>((acc, report) => {
                    const key = formatReportGroupDate(report.created_at);
                    acc[key] = [...(acc[key] ?? []), report];
                    return acc;
                  }, {});

                  return (
                    <div key={project.id} className="rounded-2xl border border-white/8 bg-white/[0.025]">
                      <button
                        type="button"
                        onClick={() => toggleProject(project.id)}
                        className="flex w-full items-center justify-between gap-3 px-3 py-3 text-left transition hover:bg-white/[0.04]"
                      >
                        <div className="min-w-0">
                          <div className={cn("truncate text-sm font-medium", hasActiveReport ? "text-cyan-100" : "text-foreground")}>
                            {project.name}
                          </div>
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
                            <div className="space-y-3">
                              {Object.entries(groupedReports).map(([dateLabel, grouped]) => (
                                <div key={dateLabel} className="space-y-1">
                                  <div className="px-3 text-[11px] font-medium uppercase tracking-[0.18em] text-muted-foreground/80">
                                    {dateLabel}
                                  </div>
                                  {grouped.map((report) => {
                                    const isActive = pathname === `/projects/${project.id}/reports/${report.analysis_run_id}`;
                                    return (
                                      <div
                                        key={report.analysis_run_id}
                                        className={cn(
                                          "group flex items-start gap-2 rounded-xl px-3 py-2 text-sm transition",
                                          isActive
                                            ? "bg-cyan-400/[0.10] text-cyan-50 ring-1 ring-cyan-300/20"
                                            : "text-muted-foreground hover:bg-white/[0.05] hover:text-foreground"
                                        )}
                                      >
                                        <Link
                                          href={`/projects/${project.id}/reports/${report.analysis_run_id}`}
                                          className="min-w-0 flex-1"
                                        >
                                          <div className="line-clamp-2">{report.title}</div>
                                        </Link>
                                        <button
                                          type="button"
                                          aria-label={`Delete report ${report.title}`}
                                          onClick={(event) =>
                                            handleDeleteReport(event, project.id, report.analysis_run_id, report.title)
                                          }
                                          className="mt-0.5 rounded-md p-1 text-rose-300/80 opacity-0 transition hover:bg-rose-500/10 hover:text-rose-200 group-hover:opacity-100"
                                          disabled={deleteReport.isPending}
                                        >
                                          <Trash2 className="h-3.5 w-3.5" />
                                        </button>
                                      </div>
                                    );
                                  })}
                                </div>
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
            ) : null}
          </div>
        </nav>
      </div>
    </aside>
  );
}
