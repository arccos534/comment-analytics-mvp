import Link from "next/link";

export function Sidebar() {
  return (
    <aside className="hidden w-72 flex-col border-r border-white/60 bg-white/50 p-6 backdrop-blur xl:flex">
      <div>
        <p className="text-xs uppercase tracking-[0.3em] text-muted-foreground">Comment Analytics</p>
        <h1 className="mt-2 text-2xl font-semibold">Signals Dashboard</h1>
      </div>
      <nav className="mt-10 space-y-2">
        <Link className="block rounded-xl px-4 py-3 text-sm font-medium transition hover:bg-muted" href="/projects">
          Projects
        </Link>
      </nav>
      <div className="mt-auto rounded-2xl bg-primary/10 p-4 text-sm text-foreground">
        Demo mode поддерживает Telegram и VK без внешних API.
      </div>
    </aside>
  );
}
