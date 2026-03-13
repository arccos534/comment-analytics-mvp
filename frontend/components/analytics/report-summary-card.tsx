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
    <Card className="bg-white/80">
      <CardHeader>
        <CardTitle>Executive summary</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4 text-sm">
        <div className="grid gap-3 md:grid-cols-2">
          <InfoItem label="Theme" value={meta.post_theme || "Not specified"} />
          <InfoItem label="Platforms" value={(meta.platforms || []).join(", ") || "All"} />
          <InfoItem
            label="Keywords"
            value={meta.post_keywords?.length ? meta.post_keywords.join(", ") : "Not specified"}
          />
          <InfoItem
            label="Coverage"
            value={`${stats.total_posts} posts / ${stats.analyzed_comments} analyzed comments`}
          />
        </div>
        {summaryText ? <p>{summaryText}</p> : null}
      </CardContent>
    </Card>
  );
}

function InfoItem({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-xl bg-muted px-3 py-3">
      <div className="text-xs uppercase tracking-wide text-muted-foreground">{label}</div>
      <div className="mt-1 font-medium">{value}</div>
    </div>
  );
}
