import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ReportComment } from "@/types/analytics";

export function CommentsSampleList({ title, comments }: { title: string; comments: ReportComment[] }) {
  return (
    <Card className="bg-white/80">
      <CardHeader>
        <CardTitle>{title}</CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        {comments.length ? (
          comments.map((comment) => (
            <div key={comment.comment_id || comment.text} className="rounded-2xl bg-muted p-4 text-sm">
              <p>{comment.text}</p>
              {comment.post_url ? (
                <a href={comment.post_url} target="_blank" className="mt-2 inline-block text-xs text-primary" rel="noreferrer">
                  Source post
                </a>
              ) : null}
            </div>
          ))
        ) : (
          <div className="text-sm text-muted-foreground">Нет подходящих комментариев.</div>
        )}
      </CardContent>
    </Card>
  );
}
