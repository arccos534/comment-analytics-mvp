import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

export function ReportSummaryCard({
  summaryText,
  highlights,
  risks,
  recommendations
}: {
  summaryText: string | null;
  highlights: string[];
  risks: string[];
  recommendations: string[];
}) {
  return (
    <Card className="bg-white/80">
      <CardHeader>
        <CardTitle>Executive summary</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4 text-sm">
        {summaryText ? <p>{summaryText}</p> : null}
        <SummaryBlock title="Highlights" items={highlights} />
        <SummaryBlock title="Risks" items={risks} />
        <SummaryBlock title="Recommendations" items={recommendations} />
      </CardContent>
    </Card>
  );
}

function SummaryBlock({ title, items }: { title: string; items: string[] }) {
  return (
    <div>
      <h4 className="font-medium">{title}</h4>
      <div className="mt-2 space-y-2">
        {items.map((item) => (
          <div key={item} className="rounded-xl bg-muted px-3 py-2">
            {item}
          </div>
        ))}
      </div>
    </div>
  );
}
