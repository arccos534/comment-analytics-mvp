import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ReportPost } from "@/types/analytics";

export function TopPostsCard({ title, posts }: { title: string; posts: ReportPost[] }) {
  return (
    <Card className="border-white/10 bg-card/70 backdrop-blur">
      <CardHeader>
        <CardTitle>{title}</CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        {posts.length ? (
          posts.map((post) => (
            <div key={post.post_id || post.post_url} className="rounded-2xl border border-border/60 bg-background/55 p-4">
              <div className="text-sm font-medium">{post.post_text || post.post_url}</div>
              <div className="mt-2 text-xs text-muted-foreground">
                score: {post.score} | comments: {post.comments_count}
              </div>
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
