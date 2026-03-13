export type Platform = "telegram" | "vk";
export type SourceType = "channel" | "community" | "post";
export type SourceStatus = "pending" | "valid" | "invalid" | "indexing" | "ready" | "failed";

export interface Source {
  id: string;
  project_id: string;
  platform: Platform;
  source_type: SourceType;
  source_url: string;
  external_source_id: string | null;
  title: string | null;
  status: SourceStatus;
  last_indexed_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface SourceValidationResult {
  url: string;
  normalized_url: string | null;
  platform: Platform | null;
  source_type: SourceType | null;
  is_valid: boolean;
  can_save: boolean;
  reason: string | null;
  external_source_id: string | null;
  title: string | null;
}

export interface SourceBulkCreateResponse {
  created: Source[];
  skipped: SourceValidationResult[];
}

export interface IndexStatusResponse {
  project_id: string;
  total_sources: number;
  status_breakdown: Record<string, number>;
  progress: {
    percent: number;
    overall_percent: number;
    current_source_title: string | null;
    current_source_index: number;
    total_sources: number;
    completed_sources: number;
    processed_posts: number;
    total_posts: number;
    posts_label: string | null;
    updated_at: string | null;
    finished_at: string | null;
  } | null;
  sources: Array<{
    id: string;
    title: string | null;
    platform: Platform;
    status: SourceStatus;
    last_indexed_at: string | null;
  }>;
}

export type IndexMode = "full" | "latest_posts" | "preset_period" | "custom_period";
export type IndexPeriodPreset = "day" | "week" | "month" | "three_months" | "six_months" | "year";

export interface StartIndexingPayload {
  mode: IndexMode;
  latest_posts_limit?: number | null;
  period_preset?: IndexPeriodPreset | null;
  period_from?: string | null;
  period_to?: string | null;
}
