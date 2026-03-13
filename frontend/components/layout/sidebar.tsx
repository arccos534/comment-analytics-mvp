import Link from "next/link";
import { Database } from "lucide-react";

export function Sidebar() {
  return (
    <aside className="hidden min-h-screen flex-col p-5 xl:flex">
      <div className="app-panel-strong flex h-full flex-col overflow-hidden px-6 py-7">
        <div>
          <p className="section-kicker">Comment Analytics</p>
          <h1 className="mt-4 text-[36px] font-semibold tracking-[-0.06em] text-foreground">Dashboard</h1>
          <p className="section-kicker mt-4">By arccos</p>
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
        </nav>
      </div>
    </aside>
  );
}
