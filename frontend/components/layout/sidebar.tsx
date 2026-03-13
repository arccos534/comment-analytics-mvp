import Link from "next/link";

export function Sidebar() {
  return (
    <aside className="hidden w-72 flex-col border-r border-white/10 bg-white/5 p-6 backdrop-blur xl:flex">
      <div>
        <p className="text-xs uppercase tracking-[0.3em] text-muted-foreground">Comment Analytics</p>
        <h1 className="mt-2 text-2xl font-semibold text-foreground">Dashboard by arccos</h1>
      </div>
      <nav className="mt-10 space-y-2">
        <Link
          className="block rounded-xl px-4 py-3 text-sm font-medium text-foreground transition hover:bg-white/5"
          href="/projects"
        >
          Projects
        </Link>
      </nav>
    </aside>
  );
}
