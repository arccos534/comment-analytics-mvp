export function Header({ title, subtitle }: { title: string; subtitle?: string }) {
  return (
    <header className="app-panel relative overflow-hidden px-6 py-6 md:px-8 md:py-7">
      <div className="absolute inset-y-0 right-0 w-56 bg-[radial-gradient(circle_at_center,rgba(84,194,239,0.12),transparent_68%)]" />
      <div className="relative flex flex-col gap-2">
        <p className="section-kicker">MVP Workspace</p>
        <h2 className="hero-title">{title}</h2>
        {subtitle ? <p className="hero-copy">{subtitle}</p> : null}
      </div>
    </header>
  );
}
