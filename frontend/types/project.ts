export interface ProjectStats {
  total_sources: number;
  total_posts: number;
  total_comments: number;
}

export interface Project {
  id: string;
  user_id: string | null;
  name: string;
  description: string | null;
  created_at: string;
  updated_at: string;
}

export interface ProjectDetail extends Project {
  stats: ProjectStats;
}
