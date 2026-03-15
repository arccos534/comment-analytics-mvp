export interface AnalysisCreatePayload {
  prompt_text: string;
  theme?: string | null;
  keywords: string[];
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

export interface ReportSnapshot {
  id: string;
  analysis_run_id: string;
  report_json: {
    meta: {
      project_id: string;
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
    };
    summary: {
      overview?: string;
      takeaways?: string[];
      confidence_assessment?: {
        level: "high" | "medium" | "low";
        reason: string;
      };
      theme_reaction_map?: ThemeReactionItem[];
      focus_evidence?: FocusEvidenceItem[];
    };
  };
  summary_text: string | null;
  created_at: string;
}

export interface ReportComment {
  comment_id: string | null;
  text: string;
  sentiment: string | null;
  relevance_score: number | null;
  post_url: string | null;
}

export interface ReportPost {
  post_id: string | null;
  post_url: string;
  post_text: string | null;
  score: number;
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
  posts_count: number;
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
