export function Header({ title, subtitle }: { title: string; subtitle?: string }) {
  return (
    <header className="flex flex-col gap-1">
      <p className="text-xs uppercase tracking-[0.3em] text-muted-foreground">MVP Workspace</p>
      <h2 className="text-3xl font-semibold">{title}</h2>
      {subtitle ? <p className="text-sm text-muted-foreground">{subtitle}</p> : null}
    </header>
  );
}
