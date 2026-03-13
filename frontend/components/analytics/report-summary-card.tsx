import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

export function ReportSummaryCard({
  summaryText,
  meta,
  stats
}: {
  summaryText: string | null;
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
      <CardContent className="space-y-4 text-sm">
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

        {summaryText ? (
          <div className="rounded-2xl border border-border/50 bg-background/40 px-4 py-4">
            <div className="whitespace-pre-line leading-7 text-foreground/92">{summaryText}</div>
          </div>
        ) : null}
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
