import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

export function TopicsCard({ topics }: { topics: Array<{ name: string; count: number; share: number }> }) {
  return (
    <Card className="border-white/10 bg-card/70 backdrop-blur">
      <CardHeader>
        <CardTitle>Top topics</CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        {topics.map((topic) => (
          <div key={topic.name} className="rounded-2xl border border-border/60 bg-background/55 p-4">
            <div className="flex items-center justify-between gap-4">
              <div className="font-medium">{topic.name}</div>
              <div className="text-sm text-muted-foreground">{Math.round(topic.share * 100)}%</div>
            </div>
            <div className="mt-2 text-sm text-muted-foreground">{topic.count} comments</div>
          </div>
        ))}
      </CardContent>
    </Card>
  );
}
