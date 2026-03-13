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
      highlights: string[];
      risks: string[];
      recommendations: string[];
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
}
