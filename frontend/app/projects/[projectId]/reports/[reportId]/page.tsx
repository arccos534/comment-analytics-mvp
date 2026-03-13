"use client";

import { useState } from "react";

import { ChevronDown, ChevronUp } from "lucide-react";

import { CommentsSampleList } from "@/components/analytics/comments-sample-list";
import { ReportSummaryCard } from "@/components/analytics/report-summary-card";
import { SentimentCard } from "@/components/analytics/sentiment-card";
import { TopPostsCard } from "@/components/analytics/top-posts-card";
import { TopicsCard } from "@/components/analytics/topics-card";
import { Header } from "@/components/layout/header";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { useAnalysisRun, useReport } from "@/hooks/use-analysis";

export default function ReportPage({ params }: { params: { projectId: string; reportId: string } }) {
  const runQuery = useAnalysisRun(params.reportId);
  const reportQuery = useReport(params.reportId, runQuery.data?.status === "completed");
  const [showTopPosts, setShowTopPosts] = useState(true);

  if (runQuery.isLoading) {
    return <div>Loading analysis...</div>;
  }

  if (!runQuery.data) {
    return <div className="text-rose-400">Analysis run not found.</div>;
  }

  if (runQuery.data.status !== "completed") {
    return (
      <Card className="border-white/10 bg-card/70 backdrop-blur">
        <CardContent className="p-6">
          Анализ сейчас в статусе <strong>{runQuery.data.status}</strong>. Страница обновится автоматически.
        </CardContent>
      </Card>
    );
  }

  if (reportQuery.isLoading || !reportQuery.data) {
    return <div>Loading report...</div>;
  }

  const report = reportQuery.data.report_json;

  return (
    <div className="space-y-8">
      <Header
        title="Report snapshot"
        subtitle={`Posts: ${report.stats.total_posts} | Comments: ${report.stats.total_comments} | Analyzed: ${report.stats.analyzed_comments}`}
      />

      <SentimentCard sentiment={report.sentiment} />

      <div className="grid gap-5 xl:grid-cols-2">
        <TopicsCard topics={report.topics} />
        <ReportSummaryCard summaryText={reportQuery.data.summary_text} meta={report.meta} stats={report.stats} />
      </div>

      <div className="grid gap-5 xl:grid-cols-3">
        <CommentsSampleList title="Positive examples" comments={report.examples.positive_comments} />
        <CommentsSampleList title="Negative examples" comments={report.examples.negative_comments} />
        <CommentsSampleList title="Neutral examples" comments={report.examples.neutral_comments} />
      </div>

      <div className="flex items-center justify-between rounded-2xl border border-white/10 bg-card/50 px-4 py-3 backdrop-blur">
        <div>
          <div className="text-sm font-medium text-foreground">Posts by engagement</div>
          <div className="text-xs text-muted-foreground">Top popular and least popular posts for the selected report scope.</div>
        </div>
        <Button variant="secondary" onClick={() => setShowTopPosts((value) => !value)}>
          {showTopPosts ? (
            <>
              <ChevronUp className="mr-2 h-4 w-4" />
              Hide
            </>
          ) : (
            <>
              <ChevronDown className="mr-2 h-4 w-4" />
              Show
            </>
          )}
        </Button>
      </div>

      {showTopPosts ? (
        <div className="grid gap-5 xl:grid-cols-2">
          <TopPostsCard title="Top popular posts" posts={report.posts.top_popular} />
          <TopPostsCard title="Top unpopular posts" posts={report.posts.top_unpopular} />
        </div>
      ) : null}
    </div>
  );
}
