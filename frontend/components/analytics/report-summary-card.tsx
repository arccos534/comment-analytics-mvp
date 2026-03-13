import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

export function ReportSummaryCard({
  summaryText,
  summary,
  meta,
  stats
}: {
  summaryText: string | null;
  summary?: {
    focus?: string;
    answer_to_prompt?: string;
    what_audience_likes?: string[];
    what_audience_dislikes?: string[];
    interest_drivers?: string[];
    limitations?: string[];
  };
  meta: {
    post_theme?: string | null;
    post_keywords?: string[];
    platforms?: string[];
  };
  stats: {
    total_posts: number;
    total_comments: number;
    analyzed_comments: number;
  };
}) {
  return (
    <Card className="border-white/10 bg-card/70 backdrop-blur">
      <CardHeader>
        <CardTitle>Сводка</CardTitle>
      </CardHeader>
      <CardContent className="space-y-5 text-sm">
        <div className="grid gap-3 md:grid-cols-2">
          <InfoItem label="Тема постов" value={meta.post_theme || "Не указана"} />
          <InfoItem label="Платформы" value={(meta.platforms || []).join(", ") || "Все"} />
          <InfoItem
            label="Ключевые слова"
            value={meta.post_keywords?.length ? meta.post_keywords.join(", ") : "Не указаны"}
          />
          <InfoItem
            label="Покрытие"
            value={`${stats.total_posts} постов / ${stats.analyzed_comments} релевантных комментариев`}
          />
        </div>

        {summary?.focus ? <SummarySection title="Контекст анализа" content={summary.focus} /> : null}
        {summary?.answer_to_prompt ? <SummarySection title="Ответ на запрос" content={summary.answer_to_prompt} /> : null}
        {summary?.what_audience_likes?.length ? (
          <ListSection title="Что нравится аудитории" items={summary.what_audience_likes} />
        ) : null}
        {summary?.what_audience_dislikes?.length ? (
          <ListSection title="Что не нравится аудитории" items={summary.what_audience_dislikes} />
        ) : null}
        {summary?.interest_drivers?.length ? (
          <ListSection title="Что вызывает интерес" items={summary.interest_drivers} />
        ) : null}
        {summary?.limitations?.length ? (
          <ListSection title="Ограничения выборки" items={summary.limitations} />
        ) : null}
        {summaryText ? <SummarySection title="Краткое резюме" content={summaryText} /> : null}
      </CardContent>
    </Card>
  );
}

function InfoItem({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-xl border border-border/60 bg-background/55 px-3 py-3">
      <div className="text-xs uppercase tracking-wide text-muted-foreground">{label}</div>
      <div className="mt-1 font-medium">{value}</div>
    </div>
  );
}

function SummarySection({ title, content }: { title: string; content: string }) {
  return (
    <div className="space-y-2">
      <div className="text-xs uppercase tracking-[0.16em] text-muted-foreground">{title}</div>
      <p className="leading-7 text-foreground/92">{content}</p>
    </div>
  );
}

function ListSection({ title, items }: { title: string; items: string[] }) {
  return (
    <div className="space-y-2">
      <div className="text-xs uppercase tracking-[0.16em] text-muted-foreground">{title}</div>
      <ul className="space-y-2">
        {items.map((item) => (
          <li key={item} className="rounded-xl border border-border/50 bg-background/45 px-3 py-3 leading-6 text-foreground/90">
            {item}
          </li>
        ))}
      </ul>
    </div>
  );
}
