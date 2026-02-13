export interface ScoredJob {
  title: string;
  company: string;
  location?: string;
  score: number;
  explanation: string;
  keywords: string[];
  url?: string;
  source: string;
}

export interface SkillGap {
  skill: string;
  importance: 'high' | 'medium' | 'low';
  category: string;
}

export interface UpskillingItem {
  skill: string;
  priority: number;
  recommended_courses: string[];
  estimated_time?: string;
}

export interface SalaryInsights {
  min_salary: number | null;
  max_salary: number | null;
  median_salary: number | null;
  currency: string;
  experience_level?: string;
  source: string;
}

export interface DecisionLogEntry {
  stage: string;
  action: string;
  reasoning: string;
  timestamp?: string;
}

export interface PipelineResults {
  session_id: string;
  status: string;
  resume_info: Record<string, unknown> | null;
  scored_jobs: ScoredJob[];
  skill_gaps: SkillGap[];
  upskilling_roadmap: UpskillingItem[];
  salary_insights: SalaryInsights | null;
  industry_trends: string[];
  final_pitch: string | null;
  summary: string | null;
  decision_log: DecisionLogEntry[];
}
