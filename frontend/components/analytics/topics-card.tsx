import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

export function TopicsCard({ topics }: { topics: Array<{ name: string; count: number; share: number }> }) {
  return (
    <Card className="bg-white/80">
      <CardHeader>
        <CardTitle>Top topics</CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        {topics.map((topic) => (
          <div key={topic.name} className="rounded-2xl bg-muted p-4">
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
