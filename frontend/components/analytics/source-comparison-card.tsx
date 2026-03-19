import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { SourceComparisonItem } from "@/types/analytics";

type SourceMetric =
  | "subscribers"
  | "views"
  | "likes"
  | "comments"
  | "reposts"
  | "engagement";

type MetricCard = {
  label: string;
  value: number;
};

function getReactionLabel(platform: string | null | undefined) {
  return (platform || "").toLowerCase() === "telegram" ? "Реакции" : "Лайки";
}

function formatPlatform(platform: string | null | undefined) {
  if (!platform) {
    return "Источник";
  }
  return platform === "vk" ? "VK" : "Telegram";
}

function getMetricDescription(metric: SourceMetric) {
  switch (metric) {
    case "subscribers":
      return "Источники отсортированы по размеру аудитории.";
    case "views":
      return "Источники отсортированы по просмотрам публикаций.";
    case "likes":
      return "Источники отсортированы по лайкам или реакциям.";
    case "comments":
      return "Источники отсортированы по комментариям.";
    case "reposts":
      return "Источники отсортированы по репостам.";
    default:
      return "Сравнение каналов и сообществ по размеру аудитории, средним метрикам и общему отклику.";
  }
}

function getMetricCards(item: SourceComparisonItem, metric: SourceMetric): MetricCard[] {
  const reactionLabel = getReactionLabel(item.platform);

  switch (metric) {
    case "subscribers":
      return [{ label: "Подписчики", value: Number(item.subscriber_count || 0) }];
    case "views":
      return [
        { label: "Просмотры в среднем", value: Number(item.avg_views_per_post || 0) },
        { label: "Просмотры суммарно", value: Number(item.views_count || 0) },
      ];
    case "likes":
      return [
        { label: `${reactionLabel} в среднем`, value: Number(item.avg_likes_per_post || 0) },
        { label: `${reactionLabel} суммарно`, value: Number(item.likes_count || 0) },
      ];
    case "comments":
      return [
        { label: "Комментарии в среднем", value: Number(item.avg_comments_per_post || 0) },
        { label: "Комментарии суммарно", value: Number(item.comments_count || 0) },
      ];
    case "reposts":
      return [
        { label: "Репосты в среднем", value: Number(item.avg_reposts_per_post || 0) },
        { label: "Репосты суммарно", value: Number(item.reposts_count || 0) },
      ];
    default:
      return [
        { label: "Подписчики", value: Number(item.subscriber_count || 0) },
        { label: "Постов", value: Number(item.posts_count || 0) },
        { label: "Просмотры в среднем", value: Number(item.avg_views_per_post || 0) },
        { label: `${reactionLabel} в среднем`, value: Number(item.avg_likes_per_post || 0) },
        { label: "Комментарии в среднем", value: Number(item.avg_comments_per_post || 0) },
        { label: "Репосты в среднем", value: Number(item.avg_reposts_per_post || 0) },
      ];
  }
}

export function SourceComparisonCard({
  items,
  title = "Сравнение источников",
  metric = "engagement",
}: {
  items: SourceComparisonItem[];
  title?: string;
  metric?: string;
}) {
  const normalizedMetric = (metric || "engagement") as SourceMetric;

  return (
    <Card className="border-white/10 bg-card/70 backdrop-blur">
      <CardHeader>
        <CardTitle>{title}</CardTitle>
        <div className="text-sm text-muted-foreground">{getMetricDescription(normalizedMetric)}</div>
      </CardHeader>
      <CardContent className="space-y-3">
        {items.length ? (
          items.map((item, index) => {
            const metricCards = getMetricCards(item, normalizedMetric);
            return (
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

                <div
                  className={`mt-3 grid gap-2 text-sm text-muted-foreground ${
                    metricCards.length === 1 ? "md:grid-cols-1 xl:grid-cols-1" : "md:grid-cols-2 xl:grid-cols-2"
                  }`}
                >
                  {metricCards.map((metricItem) => (
                    <MetricItem key={metricItem.label} label={metricItem.label} value={metricItem.value} />
                  ))}
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
            );
          })
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
      <div className="mt-1 font-medium text-foreground">{Number.isInteger(value) ? value : value.toFixed(2)}</div>
    </div>
  );
}
