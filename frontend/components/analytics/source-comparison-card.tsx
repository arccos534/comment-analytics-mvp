import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { SourceComparisonItem } from "@/types/analytics";

function getMetricLabel(platform: string | null | undefined) {
  return (platform || "").toLowerCase() === "telegram" ? "реакций" : "лайков";
}

function formatPlatform(platform: string | null | undefined) {
  if (!platform) {
    return "Источник";
  }
  return platform === "vk" ? "VK" : "Telegram";
}

export function SourceComparisonCard({
  items,
  title = "Сравнение источников",
}: {
  items: SourceComparisonItem[];
  title?: string;
}) {
  return (
    <Card className="border-white/10 bg-card/70 backdrop-blur">
      <CardHeader>
        <CardTitle>{title}</CardTitle>
        <div className="text-sm text-muted-foreground">
          Сравнение каналов и сообществ по размеру аудитории, средним метрикам и общему отклику.
        </div>
      </CardHeader>
      <CardContent className="space-y-3">
        {items.length ? (
          items.map((item, index) => (
            <div key={item.source_id} className="rounded-2xl border border-border/60 bg-background/55 p-4">
              <div className="flex flex-col gap-3">
                <div>
                  {item.source_url ? (
                    <a
                      href={item.source_url}
                      target="_blank"
                      rel="noreferrer"
                      className="text-base font-semibold text-primary transition hover:text-primary/80 hover:underline"
                    >
                      {index + 1}. {item.source_title || item.source_url || "Источник без названия"}
                    </a>
                  ) : (
                    <div className="text-base font-semibold">
                      {index + 1}. {item.source_title || item.source_url || "Источник без названия"}
                    </div>
                  )}
                  <div className="mt-1 text-sm text-muted-foreground">{formatPlatform(item.platform)}</div>
                </div>
              </div>

              <div className="mt-3 grid gap-2 text-sm text-muted-foreground md:grid-cols-2 xl:grid-cols-3">
                <MetricItem label="Подписчики" value={item.subscriber_count ?? 0} />
                <MetricItem label="Постов" value={item.posts_count} />
                <MetricItem label="Просмотры суммарно" value={item.views_count} />
                <MetricItem label={`${getMetricLabel(item.platform)} суммарно`} value={item.likes_count} />
                <MetricItem label="Комментарии суммарно" value={item.comments_count} />
                <MetricItem label="Репосты суммарно" value={item.reposts_count} />
                <MetricItem label="Просмотры в среднем" value={item.avg_views_per_post} />
                <MetricItem label={`${getMetricLabel(item.platform)} в среднем`} value={item.avg_likes_per_post} />
                <MetricItem label="Комментарии в среднем" value={item.avg_comments_per_post} />
                <MetricItem label="Репосты в среднем" value={item.avg_reposts_per_post} />
              </div>

              {item.source_url ? (
                <div className="mt-3">
                  <a
                    href={item.source_url}
                    target="_blank"
                    rel="noreferrer"
                    className="inline-flex rounded-full border border-primary/20 bg-primary/10 px-3 py-1 text-xs font-medium text-primary transition hover:bg-primary/15"
                  >
                    Check source
                  </a>
                </div>
              ) : null}
            </div>
          ))
        ) : (
          <div className="text-sm text-muted-foreground">Нет данных для сравнения источников.</div>
        )}
      </CardContent>
    </Card>
  );
}

function MetricItem({ label, value }: { label: string; value: number }) {
  return (
    <div className="rounded-xl border border-border/50 bg-background/35 px-3 py-2">
      <div className="text-xs uppercase tracking-wide text-muted-foreground">{label}</div>
      <div className="mt-1 font-medium text-foreground">{value}</div>
    </div>
  );
}
