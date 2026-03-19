"use client";

import { useEffect, useState } from "react";

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
import {
  clearActiveAnalysisRun,
  clearPendingAnalysisRequest,
  saveActiveAnalysisRun,
} from "@/lib/analysis-run-storage";
import { Card, CardContent } from "@/components/ui/card";
import { Select } from "@/components/ui/select";
import { useAnalysisRun, useReport } from "@/hooks/use-analysis";
import { AnalysisMode, ReportComment, ReportPost, ReportSnapshot, SourceComparisonItem, ThemeReactionItem } from "@/types/analytics";

const DISPLAY_OPTIONS = [3, 5, 10, 20];

const REQUESTED_COUNT_WORDS: Record<string, number> = {
  один: 1,
  одна: 1,
  одно: 1,
  одну: 1,
  одного: 1,
  два: 2,
  две: 2,
  двух: 2,
  три: 3,
  трех: 3,
  "трёх": 3,
  четыре: 4,
  четырех: 4,
  "четырёх": 4,
  пять: 5,
  пяти: 5,
  шесть: 6,
  шести: 6,
  семь: 7,
  семи: 7,
  восемь: 8,
  восьми: 8,
  девять: 9,
  девяти: 9,
  десять: 10,
  десяти: 10,
};

const REQUESTED_COUNT_WORD_PATTERN = Object.keys(REQUESTED_COUNT_WORDS)
  .sort((left, right) => right.length - left.length)
  .join("|");

type PostSection = {
  title: string;
  description?: string;
  posts: ReportPost[];
};

type ThemeCardConfig = {
  title: string;
  description: string;
  items: ThemeReactionItem[];
  emptyText?: string;
};

type TakeawayLink = {
  label: string;
  url: string;
};

type CommentSection = {
  title: string;
  comments: ReportComment[];
};

function getAnalysisMode(report: ReportSnapshot["report_json"]): AnalysisMode {
  return report.summary.primary_mode || report.summary.analysis_mode || "topic_report";
}

function parseRequestedCount(promptText?: string | null): number | null {
  const text = (promptText || "").toLowerCase();
  if (!text) {
    return null;
  }

  const patterns = [
    /(?:топ|top)\s*(\d{1,2})/i,
    /выдел(?:и|ить)?[^0-9]{0,24}(\d{1,2})/i,
    /покажи[^0-9]{0,24}(\d{1,2})/i,
    /найди[^0-9]{0,24}(\d{1,2})/i,
    /(\d{1,2})\s*(?:тем|постов|сюжетов|источников|каналов)/i,
  ];

  for (const pattern of patterns) {
    const match = text.match(pattern);
    if (!match) {
      continue;
    }
    const parsed = Number.parseInt(match[1], 10);
    if (Number.isFinite(parsed) && parsed > 0) {
      return parsed;
    }
  }

  const wordPatterns = [
    new RegExp(`(?:топ|top)\\s*(${REQUESTED_COUNT_WORD_PATTERN})\\b`, "i"),
    new RegExp(`выдел(?:и|ить)?[^a-zа-я0-9]{0,24}(${REQUESTED_COUNT_WORD_PATTERN})\\b`, "i"),
    new RegExp(`покажи[^a-zа-я0-9]{0,24}(${REQUESTED_COUNT_WORD_PATTERN})\\b`, "i"),
    new RegExp(`найди[^a-zа-я0-9]{0,24}(${REQUESTED_COUNT_WORD_PATTERN})\\b`, "i"),
    new RegExp(`(${REQUESTED_COUNT_WORD_PATTERN})\\s*(?:сам\\w+\\s+)?(?:тем|постов|сюжетов|источников|каналов)`, "i"),
  ];
  for (const pattern of wordPatterns) {
    const match = text.match(pattern);
    if (!match) {
      continue;
    }
    const parsed = REQUESTED_COUNT_WORDS[match[1]];
    if (Number.isFinite(parsed) && parsed > 0) {
      return parsed;
    }
  }
  return null;
}

function getRequestedCount(report: ReportSnapshot["report_json"]): number | null {
  const metaCount = Number(report.meta.requested_item_count || 0);
  if (Number.isFinite(metaCount) && metaCount > 0) {
    return metaCount;
  }
  return parseRequestedCount(report.meta.prompt_text);
}

function getDefaultDisplayCount(mode: AnalysisMode): number {
  switch (mode) {
    case "source_comparison":
      return 3;
    case "theme_sentiment":
    case "theme_interest":
    case "theme_popularity":
    case "theme_underperformance":
      return 5;
    case "mixed":
      return 3;
    default:
      return 5;
  }
}

function getDisplayCount(report: ReportSnapshot["report_json"], mode: AnalysisMode): number {
  return getRequestedCount(report) || getDefaultDisplayCount(mode);
}

function getRequestedSourceMetric(report: ReportSnapshot["report_json"]): string {
  return String(report.meta.requested_source_metric || "engagement");
}

function getSourceComparisonSortValue(item: SourceComparisonItem, metric: string) {
  switch (metric) {
    case "subscribers":
      return [
        Number(item.subscriber_count || 0),
        Number(item.avg_views_per_post || 0),
        Number(item.avg_likes_per_post || 0),
        Number(item.avg_comments_per_post || 0),
        Number(item.avg_reposts_per_post || 0),
      ];
    case "views":
      return [
        Number(item.avg_views_per_post || 0),
        Number(item.subscriber_count || 0),
        Number(item.avg_likes_per_post || 0),
        Number(item.avg_comments_per_post || 0),
        Number(item.avg_reposts_per_post || 0),
      ];
    case "likes":
      return [
        Number(item.avg_likes_per_post || 0),
        Number(item.avg_views_per_post || 0),
        Number(item.avg_comments_per_post || 0),
        Number(item.avg_reposts_per_post || 0),
        Number(item.subscriber_count || 0),
      ];
    case "comments":
      return [
        Number(item.avg_comments_per_post || 0),
        Number(item.avg_views_per_post || 0),
        Number(item.avg_likes_per_post || 0),
        Number(item.avg_reposts_per_post || 0),
        Number(item.subscriber_count || 0),
      ];
    case "reposts":
      return [
        Number(item.avg_reposts_per_post || 0),
        Number(item.avg_views_per_post || 0),
        Number(item.avg_likes_per_post || 0),
        Number(item.avg_comments_per_post || 0),
        Number(item.subscriber_count || 0),
      ];
    default:
      return [
        Number(item.avg_views_per_post || 0),
        Number(item.avg_likes_per_post || 0),
        Number(item.avg_comments_per_post || 0),
        Number(item.avg_reposts_per_post || 0),
        Number(item.subscriber_count || 0),
      ];
  }
}

function sortSourceComparisonItems(items: SourceComparisonItem[], metric: string) {
  return [...(items || [])].sort((left, right) => {
    const leftValues = getSourceComparisonSortValue(left, metric);
    const rightValues = getSourceComparisonSortValue(right, metric);
    for (let index = 0; index < rightValues.length; index += 1) {
      const delta = rightValues[index] - leftValues[index];
      if (delta !== 0) {
        return delta;
      }
    }
    return 0;
  });
}

function getSourceComparisonTitle(report: ReportSnapshot["report_json"], count: number): string {
  const safeCount = Math.max(count, getDisplayCount(report, "source_comparison"));
  const metric = getRequestedSourceMetric(report);
  const metricLabelMap: Record<string, string> = {
    subscribers: "по подписчикам",
    views: "по просмотрам",
    likes: "по лайкам или реакциям",
    comments: "по комментариям",
    reposts: "по репостам",
    engagement: "по совокупности метрик",
  };
  return `Топ ${safeCount} источников ${metricLabelMap[metric] || "по совокупности метрик"}`;
}

function getThemeSuccessScore(item: ThemeReactionItem): number {
  return (
    Number(item.views_count || 0) * 5 +
    Number(item.likes_count || 0) * 4 +
    Number(item.comments_count || 0) * 3 +
    Number(item.reposts_count || 0) * 2 +
    Number(item.posts_count || 0)
  );
}

function getThemeInterestScore(item: ThemeReactionItem): number {
  return (
    Number(item.views_count || 0) * 4 +
    Number(item.likes_count || 0) * 4 +
    Number(item.comments_count || 0) * 3 +
    Number(item.reposts_count || 0) * 2
  );
}

function getSuccessBucketPercent(report: ReportSnapshot["report_json"]): number {
  const raw = Number(report.meta.requested_success_bucket_percent || 0);
  return Number.isFinite(raw) && raw > 0 ? raw : 20;
}

function getUniquePostKey(post: ReportPost): string {
  return String(post.post_id || post.post_url || post.post_text || "");
}

function getSingleFocusPost(report: ReportSnapshot["report_json"]): ReportPost | null {
  const groups = [
    ...(report.posts.matched || []),
    ...(report.summary.top_negative_posts || []),
    ...(report.summary.top_positive_posts || []),
    ...(report.posts.top_reacted || []),
    ...(report.posts.top_popular || []),
  ];
  const unique: ReportPost[] = [];
  const seen = new Set<string>();
  for (const post of groups) {
    const key = getUniquePostKey(post);
    if (!key || seen.has(key)) {
      continue;
    }
    seen.add(key);
    unique.push(post);
  }
  return unique.length === 1 ? unique[0] : null;
}

function isThemeMode(mode: AnalysisMode) {
  return ["theme_sentiment", "theme_interest", "theme_popularity", "theme_underperformance", "topic_report"].includes(mode);
}

function isMetricMode(mode: AnalysisMode) {
  return ["post_popularity", "post_underperformance", "mixed"].includes(mode);
}

function getThemeCardConfig(report: ReportSnapshot["report_json"], mode: AnalysisMode): ThemeCardConfig {
  const baseItems = [...(report.summary.theme_reaction_map || [])];
  const promptModes = new Set(report.summary.prompt_modes || []);
  const displayCount = getDisplayCount(report, mode);

  if (mode === "theme_popularity") {
    const items = [...baseItems].sort((left, right) => getThemeSuccessScore(right) - getThemeSuccessScore(left));
    return {
      title: displayCount ? `Топ ${displayCount} популярных тем` : "Популярные темы",
      description: "Темы ранжированы по совокупности просмотров, реакций, комментариев и репостов ведущих постов.",
      items: items.slice(0, displayCount),
      emptyText: "Для выбранного запроса пока не удалось выделить популярные темы.",
    };
  }

  if (mode === "theme_underperformance") {
    const items = [...baseItems].sort((left, right) => getThemeSuccessScore(left) - getThemeSuccessScore(right));
    return {
      title: displayCount ? `Топ ${displayCount} непопулярных тем` : "Непопулярные темы",
      description: "Темы ранжированы по самым слабым метрикам ведущих постов внутри текущего среза.",
      items: items.slice(0, displayCount),
      emptyText: "Для выбранного запроса пока не удалось выделить непопулярные темы.",
    };
  }

  if (mode === "theme_interest") {
    const items = [...baseItems].sort((left, right) => getThemeInterestScore(right) - getThemeInterestScore(left));
    return {
      title: displayCount ? `Топ ${displayCount} тем по интересу аудитории` : "Темы с максимальным интересом",
      description: "Темы ранжированы по просмотрам, лайкам или реакциям, комментариям и репостам ведущих постов.",
      items: items.slice(0, displayCount),
      emptyText: "Для выбранного запроса пока не удалось выделить темы с выраженным интересом аудитории.",
    };
  }

  if (mode === "theme_sentiment") {
    if (promptModes.has("negative_analysis") && !promptModes.has("positive_analysis")) {
      const items = [...baseItems]
        .sort(
          (left, right) =>
            Number(right.negative_comments || 0) - Number(left.negative_comments || 0) ||
            Number(right.comments_count || 0) - Number(left.comments_count || 0)
        )
        .filter((item) => Number(item.negative_comments || 0) > Number(item.positive_comments || 0));
      return {
        title: displayCount ? `Топ ${displayCount} тем с наиболее негативной реакцией` : "Темы с наиболее негативной реакцией",
        description: "Ранжирование идёт по числу негативных релевантных комментариев. Реакция аудитории оценивается в первую очередь по тому, о чём пишут люди.",
        items: items.slice(0, displayCount),
        emptyText: "Для текущей выборки пока не удалось выделить темы с заметной негативной реакцией в комментариях.",
      };
    }

    if (promptModes.has("positive_analysis") && !promptModes.has("negative_analysis")) {
      const items = [...baseItems]
        .sort(
          (left, right) =>
            Number(right.positive_comments || 0) - Number(left.positive_comments || 0) ||
            Number(right.comments_count || 0) - Number(left.comments_count || 0)
        )
        .filter((item) => Number(item.positive_comments || 0) > Number(item.negative_comments || 0));
      return {
        title: displayCount ? `Топ ${displayCount} тем с наиболее позитивной реакцией` : "Темы с наиболее позитивной реакцией",
        description: "Ранжирование идёт по числу позитивных релевантных комментариев. Реакция аудитории оценивается в первую очередь по тому, о чём пишут люди.",
        items: items.slice(0, displayCount),
        emptyText: "Для текущей выборки пока не удалось выделить темы с заметной позитивной реакцией в комментариях.",
      };
    }
  }

  return {
    title: "Темы и реакция аудитории",
    description: "Какие сюжетные темы вызывают интерес и какой тип реакции они собирают.",
    items: baseItems.slice(0, displayCount),
    emptyText: "Для текущей выборки карта тем и реакции пока не сформировалась.",
  };
}

function getTakeawayLinks(report: ReportSnapshot["report_json"], mode: AnalysisMode): TakeawayLink[] {
  const promptModes = new Set(report.summary.prompt_modes || []);
  const links: TakeawayLink[] = [];

  const pushUniqueUrl = (label: string, url?: string | null) => {
    const normalized = (url || "").trim();
    if (!normalized || links.some((item) => item.url === normalized)) {
      return;
    }
    links.push({ label, url: normalized });
  };

  const pushUniqueLink = (label: string, posts: ReportPost[] | undefined) => {
    const target = (posts || []).find((item) => item.post_url?.trim());
    pushUniqueUrl(label, target?.post_url);
  };

  if (mode === "post_sentiment") {
    const requestedNegative = promptModes.has("most_negative_post");
    const requestedPositive = promptModes.has("most_positive_post");
    const showBoth = !requestedNegative && !requestedPositive;

    if (requestedNegative || showBoth) {
      pushUniqueLink(showBoth ? "Negative post" : "Source post", report.summary.top_negative_posts);
    }
    if (requestedPositive || showBoth) {
      pushUniqueLink(showBoth ? "Positive post" : "Source post", report.summary.top_positive_posts);
    }
  }

  if (mode === "post_popularity") {
    if (promptModes.has("most_reacted_post")) {
      pushUniqueLink("Source post", report.posts.top_reacted);
    } else if (promptModes.has("most_viewed_post")) {
      const posts = [...(report.posts.top_popular || [])].sort(
        (left, right) => Number(right.views_count || 0) - Number(left.views_count || 0)
      );
      pushUniqueLink("Source post", posts);
    } else if (promptModes.has("most_discussed_news")) {
      pushUniqueLink("Source post", report.posts.top_discussed);
    } else {
      pushUniqueLink("Source post", report.posts.top_popular);
    }
  }

  if (mode === "post_underperformance") {
    if (promptModes.has("least_reacted_post")) {
      pushUniqueLink("Source post", report.posts.top_unreacted);
    } else if (promptModes.has("least_viewed_post")) {
      const posts = [...(report.posts.top_unpopular || [])].sort(
        (left, right) => Number(left.views_count || 0) - Number(right.views_count || 0)
      );
      pushUniqueLink("Source post", posts);
    } else {
      pushUniqueLink("Source post", report.posts.top_unpopular);
    }
  }

  if (mode === "mixed") {
    const showTopBucket = promptModes.has("successful_posts_bucket");
    const showBottomBucket = promptModes.has("underperforming_posts_bucket");
    if (showTopBucket) {
      pushUniqueLink(showBottomBucket ? "Top post" : "Source post", report.posts.success_top_bucket);
    }
    if (showBottomBucket) {
      pushUniqueLink(showTopBucket ? "Bottom post" : "Source post", report.posts.success_bottom_bucket);
    }
  }

  if (mode === "source_comparison") {
    const topSource = (report.sources?.comparison || []).find((item) => item.source_url?.trim());
    pushUniqueUrl("Check source", topSource?.source_url);
  }

  if (links.length !== 1) {
    return links;
  }
  if (mode === "source_comparison") {
    return links;
  }
  return [{ ...links[0], label: "Source post" }];
}

function getPostSections(report: ReportSnapshot["report_json"], mode: AnalysisMode): PostSection[] {
  const postGroups = report.posts;
  const promptModes = new Set(report.summary.prompt_modes || []);
  const showSuccessTopBucket = promptModes.has("successful_posts_bucket");
  const showSuccessBottomBucket = promptModes.has("underperforming_posts_bucket");
  const successBucketPercent = getSuccessBucketPercent(report);
  const successBucketLabel = `${successBucketPercent}%`;
  const topPositivePosts = report.summary.top_positive_posts || [];
  const topNegativePosts = report.summary.top_negative_posts || [];

  if (mode === "source_comparison") {
    return [];
  }

  if (mode === "post_popularity") {
    return [
      {
        title: "Лидеры по лайкам и реакциям",
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
        title: `Верхние ${successBucketLabel} по успешности`,
        description: `Секция показывается только если пользователь явно просит выделить верхние ${successBucketLabel} постов.`,
        posts: showSuccessTopBucket ? postGroups.success_top_bucket || [] : [],
      },
    ];
  }

  if (mode === "post_underperformance") {
    return [
      {
        title: "Аутсайдеры по лайкам и реакциям",
        description: "Посты с наименьшим числом лайков или реакций.",
        posts: postGroups.top_unreacted || [],
      },
      {
        title: "Аутсайдеры по просмотрам",
        description: "Посты с наименьшим охватом.",
        posts: [...(postGroups.top_unpopular || [])].sort(
          (left, right) => Number(left.views_count || 0) - Number(right.views_count || 0)
        ),
      },
      {
        title: `Нижние ${successBucketLabel} по успешности`,
        description: `Секция показывается только если пользователь явно просит выделить нижние ${successBucketLabel} постов.`,
        posts: showSuccessBottomBucket ? postGroups.success_bottom_bucket || [] : [],
      },
    ];
  }

  if (mode === "mixed" && (showSuccessTopBucket || showSuccessBottomBucket)) {
    return [
      {
        title: `Верхние ${successBucketLabel} по успешности`,
        description: "Посты с лучшими сочетаниями просмотров, лайков или реакций и вторичных метрик.",
        posts: showSuccessTopBucket ? postGroups.success_top_bucket || [] : [],
      },
      {
        title: `Нижние ${successBucketLabel} по успешности`,
        description: "Посты с самыми слабыми сочетаниями просмотров, лайков или реакций в текущем срезе.",
        posts: showSuccessBottomBucket ? postGroups.success_bottom_bucket || [] : [],
      },
    ];
  }

  if (mode === "post_sentiment") {
    const requestedNegative = promptModes.has("most_negative_post");
    const requestedPositive = promptModes.has("most_positive_post");
    const showBoth = !requestedNegative && !requestedPositive;
    return [
      {
        title: "Посты с самой негативной реакцией",
        description: "Лидеры по числу негативных релевантных комментариев и признакам недовольства аудитории.",
        posts: requestedNegative || showBoth ? topNegativePosts : [],
      },
      {
        title: "Посты с самой позитивной реакцией",
        description: "Лидеры по числу позитивных релевантных комментариев и признакам поддержки аудитории.",
        posts: requestedPositive || showBoth ? topPositivePosts : [],
      },
    ];
  }

  if (["theme_popularity", "theme_underperformance", "theme_interest", "theme_sentiment"].includes(mode)) {
    return [];
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

function getCommentSections(report: ReportSnapshot["report_json"], mode: AnalysisMode): CommentSection[] {
  const sections: CommentSection[] = [];

  if (mode === "post_sentiment") {
    const promptModes = new Set(report.summary.prompt_modes || []);
    const requestedNegative = promptModes.has("most_negative_post");
    const requestedPositive = promptModes.has("most_positive_post");
    const showBoth = !requestedNegative && !requestedPositive;
    const negativeLead = report.summary.top_negative_posts?.[0];
    const positiveLead = report.summary.top_positive_posts?.[0];
    if ((requestedNegative || showBoth) && negativeLead?.negative_comment_examples?.length) {
      sections.push({
        title: "Комментарии к самому негативному посту",
        comments: negativeLead.negative_comment_examples,
      });
    }
    if ((requestedPositive || showBoth) && positiveLead?.positive_comment_examples?.length) {
      sections.push({
        title: "Комментарии к самому позитивному посту",
        comments: positiveLead.positive_comment_examples,
      });
    }
    return sections;
  }

  if (mode === "topic_report") {
    const singlePost = getSingleFocusPost(report);
    if (singlePost) {
      if (singlePost.positive_comment_examples?.length) {
        sections.push({ title: "Позитивные комментарии к ключевому посту", comments: singlePost.positive_comment_examples });
      }
      if (singlePost.negative_comment_examples?.length) {
        sections.push({ title: "Негативные комментарии к ключевому посту", comments: singlePost.negative_comment_examples });
      }
      if (singlePost.neutral_comment_examples?.length) {
        sections.push({ title: "Нейтральные комментарии к ключевому посту", comments: singlePost.neutral_comment_examples });
      }
      if (sections.length) {
        return sections;
      }
    }
  }

  return [];
}

export default function ReportPage({ params }: { params: { projectId: string; reportId: string } }) {
  const runQuery = useAnalysisRun(params.reportId);
  const reportQuery = useReport(params.reportId, runQuery.data?.status === "completed");
  const [showPostPanels, setShowPostPanels] = useState(false);
  const [postsLimit, setPostsLimit] = useState("5");

  useEffect(() => {
    const status = runQuery.data?.status;
    if (!status) {
      return;
    }
    if (status === "pending" || status === "running") {
      saveActiveAnalysisRun(params.projectId, params.reportId);
      return;
    }
    clearActiveAnalysisRun(params.projectId);
    clearPendingAnalysisRequest(params.projectId);
  }, [params.projectId, params.reportId, runQuery.data?.status]);

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
    return <div>Загрузка отчёта...</div>;
  }

  const report = reportQuery.data.report_json;
  const visibleLimit = Number.parseInt(postsLimit, 10) || 5;
  const analysisMode = getAnalysisMode(report);
  const isSourceMode = analysisMode === "source_comparison";
  const themeCard = getThemeCardConfig(report, analysisMode);
  const hasThemes = themeCard.items.length > 0;
  const hasComments = report.stats.analyzed_comments > 0;
  const postSections = getPostSections(report, analysisMode).filter((section) => section.posts.length > 0);
  const commentSections = getCommentSections(report, analysisMode);
  const sourceMetric = getRequestedSourceMetric(report);
  const comparisonItems = sortSourceComparisonItems(report.sources?.comparison || [], sourceMetric).slice(
    0,
    getDisplayCount(report, analysisMode)
  );
  const takeawayLinks = getTakeawayLinks(report, analysisMode);

  const showSentimentCard = analysisMode === "topic_report" && hasComments;
  const showTopicsCard = analysisMode === "topic_report" && report.topics.length > 0;
  const showThemeCard = hasThemes && isThemeMode(analysisMode);
  const showGenericComments = analysisMode === "topic_report" && hasComments && commentSections.length === 0;
  const showPostPanelsToggle = postSections.length > 0;
  const topGridClass = isSourceMode ? "xl:grid-cols-[1.2fr_0.8fr]" : showTopicsCard ? "xl:grid-cols-2" : "xl:grid-cols-1";

  return (
    <div className="space-y-8">
      <Header
        title="Снимок отчёта"
        subtitle={`Постов: ${report.stats.total_posts} | Комментариев: ${report.stats.total_comments} | Проанализировано: ${report.stats.analyzed_comments}`}
      />

      {showSentimentCard ? <SentimentCard sentiment={report.sentiment} /> : null}

      <div className={`grid gap-5 ${topGridClass}`}>
        {showTopicsCard ? <TopicsCard topics={report.topics} /> : null}
        <ReportSummaryCard
          summaryText={reportQuery.data.summary_text}
          meta={report.meta}
          stats={report.stats}
          takeaways={report.summary.takeaways || []}
          analysisMode={analysisMode}
          takeawayLinks={takeawayLinks}
        />
        {isSourceMode ? (
          <SourceComparisonCard
            items={comparisonItems}
            title={getSourceComparisonTitle(report, comparisonItems.length)}
            metric={sourceMetric}
          />
        ) : null}
      </div>

      {showThemeCard ? (
        <ThemeReactionCard
          items={themeCard.items}
          confidence={report.summary.confidence_assessment}
          title={themeCard.title}
          description={themeCard.description}
          emptyText={themeCard.emptyText}
        />
      ) : null}

      {commentSections.length ? (
        <div className="grid gap-5 xl:grid-cols-3">
          {commentSections.map((section) => (
            <CommentsSampleList key={section.title} title={section.title} comments={section.comments} />
          ))}
        </div>
      ) : null}

      {showGenericComments ? (
        <div className="grid gap-5 xl:grid-cols-3">
          <CommentsSampleList title="Позитивные примеры" comments={report.examples.positive_comments} />
          <CommentsSampleList title="Негативные примеры" comments={report.examples.negative_comments} />
          <CommentsSampleList title="Нейтральные примеры" comments={report.examples.neutral_comments} />
        </div>
      ) : null}

      {showPostPanelsToggle ? (
        <>
          <div className="flex flex-col gap-4 rounded-2xl border border-white/10 bg-card/50 px-4 py-4 backdrop-blur md:flex-row md:items-center md:justify-between">
            <div>
              <div className="text-sm font-medium text-foreground">Посты и лидеры выборки</div>
              <div className="text-xs text-muted-foreground">
                Набор карточек подстраивается под задачу: популярные посты, слабые посты, реакция на посты или смешанный режим.
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
              {postSections.map((section) => (
                <TopPostsCard
                  key={section.title}
                  title={section.title}
                  description={section.description}
                  posts={section.posts.slice(0, visibleLimit)}
                />
              ))}
            </div>
          ) : null}
        </>
      ) : null}
    </div>
  );
}
