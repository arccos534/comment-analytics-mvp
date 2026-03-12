import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { formatPercent } from "@/lib/utils";

export function SentimentCard({ sentiment }: { sentiment: { positive_percent: number; negative_percent: number; neutral_percent: number } }) {
  return (
    <Card className="bg-white/80">
      <CardHeader>
        <CardTitle>Sentiment</CardTitle>
      </CardHeader>
      <CardContent className="grid gap-3 sm:grid-cols-3">
        <Metric label="Positive" value={formatPercent(sentiment.positive_percent)} />
        <Metric label="Negative" value={formatPercent(sentiment.negative_percent)} />
        <Metric label="Neutral" value={formatPercent(sentiment.neutral_percent)} />
      </CardContent>
    </Card>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-2xl bg-muted p-4">
      <div className="text-sm text-muted-foreground">{label}</div>
      <div className="mt-2 text-2xl font-semibold">{value}</div>
    </div>
  );
}
