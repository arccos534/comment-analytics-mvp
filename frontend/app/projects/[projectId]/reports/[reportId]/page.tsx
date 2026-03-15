"use client";

import { useState } from "react";

import { ChevronDown, ChevronUp } from "lucide-react";

import { CommentsSampleList } from "@/components/analytics/comments-sample-list";
import { ReportSummaryCard } from "@/components/analytics/report-summary-card";
import { SentimentCard } from "@/components/analytics/sentiment-card";
import { ThemeReactionCard } from "@/components/analytics/theme-reaction-card";
import { TopPostsCard } from "@/components/analytics/top-posts-card";
import { TopicsCard } from "@/components/analytics/topics-card";
import { Header } from "@/components/layout/header";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Select } from "@/components/ui/select";
import { useAnalysisRun, useReport } from "@/hooks/use-analysis";

const DISPLAY_OPTIONS = [3, 5, 10, 20];

export default function ReportPage({ params }: { params: { projectId: string; reportId: string } }) {
  const runQuery = useAnalysisRun(params.reportId);
  const reportQuery = useReport(params.reportId, runQuery.data?.status === "completed");
  const [showPostPanels, setShowPostPanels] = useState(false);
  const [postsLimit, setPostsLimit] = useState("5");

  if (runQuery.isLoading) {
    return <div>Загрузка анализа...</div>;
  }

  if (!runQuery.data) {
    return <div className="text-rose-400">Аналитический запуск не найден.</div>;
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
    return <div>Загрузка отчета...</div>;
  }

  const report = reportQuery.data.report_json;
  const visibleLimit = Number.parseInt(postsLimit, 10) || 5;

  return (
    <div className="space-y-8">
      <Header
        title="Снимок отчета"
        subtitle={`Постов: ${report.stats.total_posts} | Комментариев: ${report.stats.total_comments} | Проанализировано: ${report.stats.analyzed_comments}`}
      />

      <SentimentCard sentiment={report.sentiment} />

      <div className="grid gap-5 xl:grid-cols-2">
        <TopicsCard topics={report.topics} />
        <ReportSummaryCard
          summaryText={reportQuery.data.summary_text}
          meta={report.meta}
          stats={report.stats}
          takeaways={report.summary.takeaways || []}
        />
      </div>

      <ThemeReactionCard
        items={report.summary.theme_reaction_map || []}
        confidence={report.summary.confidence_assessment}
      />

      <div className="grid gap-5 xl:grid-cols-3">
        <CommentsSampleList title="Позитивные примеры" comments={report.examples.positive_comments} />
        <CommentsSampleList title="Негативные примеры" comments={report.examples.negative_comments} />
        <CommentsSampleList title="Нейтральные примеры" comments={report.examples.neutral_comments} />
      </div>

      <div className="flex flex-col gap-4 rounded-2xl border border-white/10 bg-card/50 px-4 py-4 backdrop-blur md:flex-row md:items-center md:justify-between">
        <div>
          <div className="text-sm font-medium text-foreground">Посты в выборке</div>
          <div className="text-xs text-muted-foreground">
            Посты, попавшие в анализ, а также самые популярные и наименее популярные посты в текущей выборке.
          </div>
        </div>
        <div className="flex flex-wrap items-center gap-3">
          <div className="flex items-center gap-2 text-sm text-muted-foreground">
            <span>Показывать</span>
            <Select className="h-10 w-24 bg-card/70" value={postsLimit} onChange={(event) => setPostsLimit(event.target.value)}>
              {DISPLAY_OPTIONS.map((option) => (
                <option key={option} value={String(option)}>
                  {option}
                </option>
              ))}
            </Select>
          </div>
          <Button variant="secondary" onClick={() => setShowPostPanels((value) => !value)}>
            {showPostPanels ? (
              <>
                <ChevronUp className="mr-2 h-4 w-4" />
                Скрыть посты
              </>
            ) : (
              <>
                <ChevronDown className="mr-2 h-4 w-4" />
                Показать посты
              </>
            )}
          </Button>
        </div>
      </div>

      {showPostPanels ? (
        <div className="grid gap-5 xl:grid-cols-3">
          <TopPostsCard title="Посты в выборке" posts={(report.posts.matched || []).slice(0, visibleLimit)} />
          <TopPostsCard title="Топ популярных постов" posts={(report.posts.top_popular || []).slice(0, visibleLimit)} />
          <TopPostsCard title="Топ непопулярных постов" posts={(report.posts.top_unpopular || []).slice(0, visibleLimit)} />
        </div>
      ) : null}
    </div>
  );
}
