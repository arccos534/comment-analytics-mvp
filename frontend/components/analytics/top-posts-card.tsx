import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ReportPost } from "@/types/analytics";

function getEngagementLabel(post: ReportPost) {
  return (post.platform || "").toLowerCase() === "telegram" ? "реакций" : "лайков";
}

function formatMetrics(post: ReportPost) {
  const parts: string[] = [];
  const views = Number(post.views_count || 0);
  const likes = Number(post.likes_count || 0);
  const comments = Number(post.comments_count || 0);
  const reposts = Number(post.reposts_count || 0);

  if (views > 0) {
    parts.push(`${views} просмотров`);
  }
  parts.push(`${likes} ${getEngagementLabel(post)}`);
  parts.push(`${comments} комментариев`);
  parts.push(`${reposts} репостов`);
  return parts.join(" • ");
}

export function TopPostsCard({
  title,
  description,
  posts,
}: {
  title: string;
  description?: string;
  posts: ReportPost[];
}) {
  return (
    <Card className="border-white/10 bg-card/70 backdrop-blur">
      <CardHeader>
        <CardTitle>{title}</CardTitle>
        {description ? <div className="text-sm text-muted-foreground">{description}</div> : null}
      </CardHeader>
      <CardContent className="space-y-3">
        {posts.length ? (
          posts.map((post, index) => (
            <div
              key={post.post_id || post.post_url || `${title}-${index}`}
              className="rounded-2xl border border-border/60 bg-background/55 p-4"
            >
              <div className="text-sm font-medium leading-6">{post.post_text || post.post_url || "Пост без текста"}</div>
              <div className="mt-2 text-xs text-muted-foreground">{formatMetrics(post)}</div>
              {post.source_title ? (
                <div className="mt-1 text-xs text-muted-foreground/80">{post.source_title}</div>
              ) : null}
              {post.post_url ? (
                <a
                  href={post.post_url}
                  target="_blank"
                  rel="noreferrer"
                  className="mt-3 inline-flex rounded-full border border-primary/20 bg-primary/10 px-3 py-1 text-xs font-medium text-primary transition hover:bg-primary/15"
                >
                  Source post
                </a>
              ) : null}
            </div>
          ))
        ) : (
          <div className="text-sm text-muted-foreground">Нет данных.</div>
        )}
      </CardContent>
    </Card>
  );
}
