"use client";

import { ThemeReactionItem } from "@/types/analytics";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

const CONFIDENCE_STYLES: Record<string, string> = {
  high: "border-emerald-400/20 bg-emerald-400/10 text-emerald-200",
  medium: "border-amber-400/20 bg-amber-400/10 text-amber-200",
  low: "border-rose-400/20 bg-rose-400/10 text-rose-200",
};

function getConfidenceLabel(level: "high" | "medium" | "low") {
  if (level === "high") {
    return "Высокая уверенность";
  }
  if (level === "medium") {
    return "Средняя уверенность";
  }
  return "Низкая уверенность";
}

function getEngagementLabel(item: ThemeReactionItem) {
  const platform = (item.platform || item.leading_post.platform || "").toLowerCase();
  return platform === "telegram" ? "реакций" : "лайков";
}

export function ThemeReactionCard({
  items,
  confidence,
}: {
  items: ThemeReactionItem[];
  confidence?: {
    level: "high" | "medium" | "low";
    reason: string;
  };
}) {
  return (
    <Card className="border-white/10 bg-card/70 backdrop-blur">
      <CardHeader className="flex flex-row items-start justify-between gap-4">
        <div>
          <CardTitle>Темы и реакция аудитории</CardTitle>
          <div className="mt-1 text-sm text-muted-foreground">
            Какие сюжетные темы вызывают интерес и какой тип реакции они собирают.
          </div>
        </div>
        {confidence ? (
          <div
            className={`rounded-full border px-3 py-1 text-xs font-medium uppercase tracking-wide ${
              CONFIDENCE_STYLES[confidence.level] ?? CONFIDENCE_STYLES.low
            }`}
          >
            {getConfidenceLabel(confidence.level)}
          </div>
        ) : null}
      </CardHeader>
      <CardContent className="space-y-4">
        {confidence ? (
          <div className="rounded-2xl border border-border/60 bg-background/45 px-4 py-3 text-sm text-muted-foreground">
            {confidence.reason}
          </div>
        ) : null}

        {items.length ? (
          <div className="space-y-3">
            {items.map((item) => (
              <div key={item.theme} className="rounded-2xl border border-border/60 bg-background/50 p-4">
                <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
                  <div>
                    <div className="text-base font-semibold">{item.theme}</div>
                    <div className="mt-1 text-sm text-muted-foreground">
                      {item.posts_count} постов · {item.comments_count} комментариев · {item.likes_count}{" "}
                      {getEngagementLabel(item)} · {item.reposts_count} репостов
                    </div>
                  </div>
                  <div className="flex flex-wrap gap-2 text-xs">
                    <span className="rounded-full border border-cyan-400/20 bg-cyan-400/10 px-2.5 py-1 text-cyan-200">
                      Интерес: {item.interest_level}
                    </span>
                    <span className="rounded-full border border-white/10 bg-white/5 px-2.5 py-1 text-foreground/85">
                      Реакция: {item.reaction_tendency}
                    </span>
                  </div>
                </div>

                <div className="mt-3 grid gap-2 text-sm text-muted-foreground md:grid-cols-3">
                  <div className="rounded-xl border border-border/50 bg-background/35 px-3 py-2">
                    Позитивных: {item.positive_comments}
                  </div>
                  <div className="rounded-xl border border-border/50 bg-background/35 px-3 py-2">
                    Негативных: {item.negative_comments}
                  </div>
                  <div className="rounded-xl border border-border/50 bg-background/35 px-3 py-2">
                    Нейтральных: {item.neutral_comments}
                  </div>
                </div>

                <div className="mt-3 rounded-xl border border-border/50 bg-background/35 px-3 py-3">
                  <div className="text-xs uppercase tracking-wide text-muted-foreground">Ведущий пост по теме</div>
                  <div className="mt-2 text-sm leading-6 text-foreground/92">
                    {item.leading_post.post_text || "Нет текста поста"}
                  </div>
                  {item.leading_post.post_url ? (
                    <a
                      href={item.leading_post.post_url}
                      target="_blank"
                      rel="noreferrer"
                      className="mt-3 inline-flex rounded-full border border-primary/20 bg-primary/10 px-3 py-1 text-xs font-medium text-primary transition hover:bg-primary/15"
                    >
                      Source post
                    </a>
                  ) : null}
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="rounded-2xl border border-border/60 bg-background/45 px-4 py-5 text-sm text-muted-foreground">
            Для текущей выборки карта тем и реакции пока не сформировалась.
          </div>
        )}
      </CardContent>
    </Card>
  );
}
