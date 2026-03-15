import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { AnalysisMode } from "@/types/analytics";

const MODE_LABELS: Record<AnalysisMode, string> = {
  source_comparison: "Сравнение источников",
  post_popularity: "Популярность постов",
  post_underperformance: "Слабые посты",
  theme_sentiment: "Темы и тональность",
  theme_interest: "Темы и интерес аудитории",
  topic_report: "Тематический отчет",
  excel_export: "Табличный режим",
  mixed: "Смешанный режим",
};

export function ReportSummaryCard({
  summaryText,
  meta,
  stats,
  takeaways,
  analysisMode,
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
  takeaways?: string[];
  analysisMode?: AnalysisMode;
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

        {analysisMode ? <ModeBadge mode={analysisMode} /> : null}

        {takeaways?.length ? (
          <div className="space-y-2 rounded-2xl border border-cyan-400/15 bg-cyan-400/[0.06] px-4 py-4">
            <div className="text-xs uppercase tracking-[0.18em] text-cyan-200/80">Top takeaways</div>
            <div className="space-y-2">
              {takeaways.map((item) => (
                <div key={item} className="rounded-xl border border-white/8 bg-background/35 px-3 py-3 text-foreground/95">
                  {item}
                </div>
              ))}
            </div>
          </div>
        ) : null}

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

function ModeBadge({ mode }: { mode: AnalysisMode }) {
  return (
    <div className="inline-flex rounded-full border border-white/10 bg-background/40 px-3 py-1 text-xs font-medium text-muted-foreground">
      Режим анализа: {MODE_LABELS[mode]}
    </div>
  );
}
