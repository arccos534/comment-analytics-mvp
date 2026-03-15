"use client";

import { useState } from "react";

import { ChevronDown, ChevronUp } from "lucide-react";

import { CommentsSampleList } from "@/components/analytics/comments-sample-list";
import { ReportSummaryCard } from "@/components/analytics/report-summary-card";
import { SentimentCard } from "@/components/analytics/sentiment-card";
import { SourceComparisonCard } from "@/components/analytics/source-comparison-card";
import { ThemeReactionCard } from "@/components/analytics/theme-reaction-card";
import { TopPostsCard } from "@/components/analytics/top-posts-card";
import { TopicsCard } from "@/components/analytics/topics-card";
import { Header } from "@/components/layout/header";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Select } from "@/components/ui/select";
import { useAnalysisRun, useReport } from "@/hooks/use-analysis";
import { AnalysisMode, ReportPost, ReportSnapshot } from "@/types/analytics";

const DISPLAY_OPTIONS = [3, 5, 10, 20];

type PostSection = {
  title: string;
  description?: string;
  posts: ReportPost[];
};

function getAnalysisMode(report: ReportSnapshot["report_json"]): AnalysisMode {
  return report.summary.primary_mode || report.summary.analysis_mode || "topic_report";
}

function getPostSections(report: ReportSnapshot["report_json"], mode: AnalysisMode): PostSection[] {
  const postGroups = report.posts;
  const promptModes = new Set(report.summary.prompt_modes || []);
  const showSuccessTopBucket = promptModes.has("successful_posts_bucket");
  const showSuccessBottomBucket = promptModes.has("underperforming_posts_bucket");

  if (mode === "source_comparison") {
    return [
      {
        title: "Лидеры по реакциям",
        description: "Посты, которые лучше всего показывают сильный отклик внутри выбранных источников.",
        posts: postGroups.top_reacted || [],
      },
      {
        title: "Лидеры по обсуждаемости",
        description: "Публикации с наибольшим числом комментариев.",
        posts: postGroups.top_discussed || [],
      },
      {
        title: "Лидеры по успешности",
        description: "Верхние 20% по просмотрам, реакциям и комментариям.",
        posts: showSuccessTopBucket ? postGroups.success_top_bucket || [] : [],
      },
    ];
  }

  if (mode === "post_popularity") {
    return [
      {
        title: "Лидеры по реакциям",
        description: "Приоритетно по лайкам или реакциям, затем по просмотрам и комментариям.",
        posts: postGroups.top_reacted || [],
      },
      {
        title: "Лидеры по просмотрам",
        description: "Посты с наибольшим охватом.",
        posts: [...(postGroups.top_popular || [])].sort(
          (left, right) => Number(right.views_count || 0) - Number(left.views_count || 0)
        ),
      },
      {
        title: "Верхние 20% по успешности",
        description: "Самые сильные посты по совокупности доступных метрик.",
        posts: showSuccessTopBucket ? postGroups.success_top_bucket || [] : [],
      },
    ];
  }

  if (mode === "post_underperformance") {
    return [
      {
        title: "Аутсайдеры по реакциям",
        description: "Посты с наименьшим числом лайков или реакций.",
        posts: postGroups.top_unreacted || [],
      },
      {
        title: "Аутсайдеры по обсуждаемости",
        description: "Публикации с минимальным числом комментариев.",
        posts: postGroups.top_undiscussed || [],
      },
      {
        title: "Нижние 20% по успешности",
        description: "Посты с самыми слабыми доступными метриками.",
        posts: showSuccessBottomBucket ? postGroups.success_bottom_bucket || [] : [],
      },
    ];
  }

  return [
    {
      title: "Посты в выборке",
      description: "Публикации, которые реально попали в текущий аналитический срез.",
      posts: postGroups.matched || [],
    },
    {
      title: "Топ популярных постов",
      description: "Лидеры по просмотрам, реакциям и комментариям внутри выборки.",
      posts: postGroups.top_popular || [],
    },
    {
      title: "Топ непопулярных постов",
      description: "Публикации с самыми слабыми метриками в текущем срезе.",
      posts: postGroups.top_unpopular || [],
    },
  ];
}

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
  const analysisMode = getAnalysisMode(report);
  const isSourceMode = analysisMode === "source_comparison";
  const postSections = getPostSections(report, analysisMode);
  const comparisonItems = report.sources?.comparison || [];
  const hasThemes = (report.summary.theme_reaction_map || []).length > 0;
  const hasComments = report.stats.analyzed_comments > 0;

  return (
    <div className="space-y-8">
      <Header
        title="Снимок отчета"
        subtitle={`Постов: ${report.stats.total_posts} | Комментариев: ${report.stats.total_comments} | Проанализировано: ${report.stats.analyzed_comments}`}
      />

      {!isSourceMode && hasComments ? <SentimentCard sentiment={report.sentiment} /> : null}

      <div className={`grid gap-5 ${isSourceMode ? "xl:grid-cols-[1.2fr_0.8fr]" : "xl:grid-cols-2"}`}>
        {!isSourceMode ? <TopicsCard topics={report.topics} /> : null}
        <ReportSummaryCard
          summaryText={reportQuery.data.summary_text}
          meta={report.meta}
          stats={report.stats}
          takeaways={report.summary.takeaways || []}
          analysisMode={analysisMode}
        />
        {isSourceMode ? <SourceComparisonCard items={comparisonItems} /> : null}
      </div>

      {!isSourceMode && hasThemes ? (
        <ThemeReactionCard
          items={report.summary.theme_reaction_map || []}
          confidence={report.summary.confidence_assessment}
        />
      ) : null}

      {!isSourceMode && hasComments ? (
        <div className="grid gap-5 xl:grid-cols-3">
          <CommentsSampleList title="Позитивные примеры" comments={report.examples.positive_comments} />
          <CommentsSampleList title="Негативные примеры" comments={report.examples.negative_comments} />
          <CommentsSampleList title="Нейтральные примеры" comments={report.examples.neutral_comments} />
        </div>
      ) : null}

      <div className="flex flex-col gap-4 rounded-2xl border border-white/10 bg-card/50 px-4 py-4 backdrop-blur md:flex-row md:items-center md:justify-between">
        <div>
          <div className="text-sm font-medium text-foreground">Посты и лидеры выборки</div>
          <div className="text-xs text-muted-foreground">
            Набор карточек подстраивается под задачу: сравнение источников, поиск лидеров, аутсайдеров или тематический отчет.
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
          {postSections.filter((section) => section.posts.length > 0).map((section) => (
            <TopPostsCard
              key={section.title}
              title={section.title}
              description={section.description}
              posts={section.posts.slice(0, visibleLimit)}
            />
          ))}
        </div>
      ) : null}
    </div>
  );
}
