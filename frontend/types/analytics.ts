export interface AnalysisCreatePayload {
  prompt_text: string;
  theme?: string | null;
  keywords: string[];
  analysis_mode_override?: AnalysisMode | "auto" | null;
  period_from?: string | null;
  period_to?: string | null;
  platforms: ("telegram" | "vk")[];
  source_ids: string[];
}

export interface AnalysisRun {
  id: string;
  project_id: string;
  prompt_text: string;
  theme: string | null;
  keywords_json: string[] | null;
  period_from: string | null;
  period_to: string | null;
  filters_json: {
    platforms?: string[];
    source_ids?: string[];
    analysis_mode_override?: AnalysisMode | null;
  } | null;
  status: "pending" | "running" | "completed" | "failed";
  created_at: string;
  finished_at: string | null;
}

export interface SavedReportItem {
  analysis_run_id: string;
  title: string;
  created_at: string;
}

export interface ProjectReportsTreeItem {
  project_id: string;
  project_name: string;
  reports: SavedReportItem[];
}

export type AnalysisMode =
  | "source_comparison"
  | "post_popularity"
  | "post_underperformance"
  | "post_sentiment"
  | "theme_sentiment"
  | "theme_interest"
  | "theme_popularity"
  | "theme_underperformance"
  | "topic_report"
  | "excel_export"
  | "mixed";

export interface ReportComment {
  comment_id: string | null;
  text: string;
  sentiment: string | null;
  relevance_score: number | null;
  post_url: string | null;
}

export interface ReportPost {
  post_id: string | null;
  post_url: string | null;
  post_text: string | null;
  platform?: string | null;
  source_title?: string | null;
  source_url?: string | null;
  score?: number | null;
  views_count?: number | null;
  comments_count: number;
  relevant_comments_count?: number | null;
  positive_relevant_comments_count?: number | null;
  negative_relevant_comments_count?: number | null;
  neutral_relevant_comments_count?: number | null;
  likes_count?: number | null;
  reposts_count?: number | null;
  reaction_tendency?: string | null;
}

export interface ThemeReactionItem {
  theme: string;
  platform?: string | null;
  posts_count: number;
  views_count?: number;
  comments_count: number;
  likes_count: number;
  reposts_count: number;
  interest_level: string;
  reaction_tendency: string;
  positive_comments: number;
  negative_comments: number;
  neutral_comments: number;
  leading_post: ReportPost;
}

export interface FocusEvidenceItem {
  matched_terms: string[];
  post: ReportPost;
}

export interface SourceComparisonItem {
  source_id: string;
  source_title: string | null;
  source_url: string | null;
  platform: string | null;
  subscriber_count?: number | null;
  posts_count: number;
  views_count: number;
  comments_count: number;
  relevant_comments_count: number;
  positive_relevant_comments_count?: number | null;
  negative_relevant_comments_count?: number | null;
  neutral_relevant_comments_count?: number | null;
  likes_count: number;
  reposts_count: number;
  avg_views_per_post: number;
  avg_comments_per_post: number;
  avg_likes_per_post: number;
  avg_reposts_per_post: number;
  score?: number | null;
}

export interface ReportSummary {
  overview?: string;
  takeaways?: string[];
  analysis_mode?: AnalysisMode;
  primary_mode?: AnalysisMode;
  prompt_modes?: string[];
  secondary_modes?: string[];
  analysis_axes?: string[];
  request_contract?: string[];
  answer_strategy?: {
    opening_style?: string;
    must_cover?: string[];
    answer_shape?: string;
  };
  confidence_assessment?: {
    level: "high" | "medium" | "low";
    reason: string;
  };
  top_positive_posts?: ReportPost[];
  top_negative_posts?: ReportPost[];
  theme_reaction_map?: ThemeReactionItem[];
  focus_evidence?: FocusEvidenceItem[];
}

export interface ReportSnapshot {
  id: string;
  analysis_run_id: string;
  report_json: {
    meta: {
      project_id: string;
      prompt_text?: string | null;
      post_theme?: string | null;
      post_keywords?: string[];
      requested_success_bucket_percent?: number | null;
      period_from: string | null;
      period_to: string | null;
      platforms: string[];
      source_ids: string[];
    };
    stats: {
      total_posts: number;
      total_comments: number;
      analyzed_comments: number;
    };
    sentiment: {
      positive_percent: number;
      negative_percent: number;
      neutral_percent: number;
    };
    topics: Array<{
      name: string;
      count: number;
      share: number;
    }>;
    insights: {
      liked_patterns: string[];
      disliked_patterns: string[];
    };
    examples: {
      positive_comments: ReportComment[];
      negative_comments: ReportComment[];
      neutral_comments: ReportComment[];
    };
    posts: {
      matched: ReportPost[];
      top_popular: ReportPost[];
      top_unpopular: ReportPost[];
      top_reacted?: ReportPost[];
      top_unreacted?: ReportPost[];
      top_discussed?: ReportPost[];
      top_undiscussed?: ReportPost[];
      success_top_bucket?: ReportPost[];
      success_bottom_bucket?: ReportPost[];
    };
    sources?: {
      comparison?: SourceComparisonItem[];
    };
    summary: ReportSummary;
  };
  summary_text: string | null;
  created_at: string;
}
