import Link from "next/link";
import { BarChart3, Database, Sparkles } from "lucide-react";

export function Sidebar() {
  return (
    <aside className="hidden min-h-screen flex-col p-5 xl:flex">
      <div className="app-panel-strong flex h-full flex-col overflow-hidden px-6 py-7">
        <div className="flex items-start justify-between">
          <div>
            <p className="section-kicker">Comment Analytics</p>
            <h1 className="mt-3 text-[30px] font-semibold tracking-[-0.05em] text-foreground">Dashboard by arccos</h1>
            <p className="mt-3 text-sm leading-6 text-slate-300/68">
              Темный рабочий контур для мониторинга Telegram и VK, с фокусом на смысл, сигналы и скорость реакции.
            </p>
          </div>
          <div className="rounded-2xl border border-cyan-400/20 bg-cyan-400/10 p-3 text-cyan-200">
            <Sparkles className="h-5 w-5" />
          </div>
        </div>

        <div className="mt-8 rounded-[24px] border border-white/10 bg-white/[0.03] p-4">
          <div className="flex items-center gap-3 text-sm text-slate-200">
            <div className="rounded-2xl bg-white/5 p-2 text-cyan-200">
              <BarChart3 className="h-4 w-4" />
            </div>
            <span>Signals, topics, sentiment</span>
          </div>
          <div className="mt-3 flex items-center gap-3 text-sm text-slate-300/75">
            <div className="rounded-2xl bg-white/5 p-2 text-emerald-200">
              <Database className="h-4 w-4" />
            </div>
            <span>Projects, sources and report snapshots</span>
          </div>
        </div>

        <nav className="mt-8 space-y-3">
          <Link
            className="group flex items-center gap-3 rounded-[22px] border border-white/10 bg-white/[0.04] px-4 py-3.5 text-sm font-medium text-foreground transition hover:border-cyan-300/20 hover:bg-white/[0.07]"
            href="/projects"
          >
            <span className="rounded-xl bg-cyan-400/10 p-2 text-cyan-200 transition group-hover:bg-cyan-400/15">
              <Database className="h-4 w-4" />
            </span>
            Projects
          </Link>
        </nav>

        <div className="mt-auto rounded-[24px] border border-white/10 bg-[linear-gradient(180deg,rgba(84,194,239,0.08),rgba(255,255,255,0.03))] p-4">
          <div className="text-xs uppercase tracking-[0.28em] text-cyan-100/55">Workspace mode</div>
          <div className="mt-3 text-sm leading-6 text-slate-200">
            Собирайте каналы, отслеживайте реакцию аудитории и быстро переходите от шума к понятным выводам.
          </div>
        </div>
      </div>
    </aside>
  );
}
