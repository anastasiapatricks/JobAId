export interface ScoredJob {
  title: string;
  company: string;
  location?: string;
  score: number;
  explanation?: string;
  keywords?: string[];
  description?: string;
  url?: string;
  salary_min?: number | null;
  salary_max?: number | null;
  created_at?: string;
  category?: string;
  source?: string;
}

export interface SkillTriageEntry {
  title: string;
  company: string;
  score: number;
  skills_matched: string[];
  skills_missing: string[];
  match_ratio: number;
}

export interface SkillGap {
  skill: string;
  importance?: string;
  category?: string;
}

export interface UpskillingItem {
  skill: string;
  priority?: number;
  recommended_courses?: string[];
  estimated_time?: string;
}

export interface SalaryInsights {
  min_salary?: number | null;
  max_salary?: number | null;
  median_salary?: number | null;
  currency?: string;
  experience_level?: string;
  source?: string;
}

export interface DecisionLogEntry {
  stage: string;
  action: string;
  reasoning?: string;
  timestamp?: string;
}

export interface ExplainabilityTrace {
  stage?: string;
  agent?: string;
  agent_name?: string;
  prompt_version?: string;
  confidence?: number;
  reasoning?: string;
  decision_log?: DecisionLogEntry[];
  input_summary?: string;
  output_summary?: string;
  grounding_checks?: string[];
  grounding_score?: number;
  fairness_checks?: string[];
  skill_attribution?: Record<string, number>;
  feature_attributions?: Record<string, unknown>;
  perturbation_analysis?: Record<string, unknown>;
  sources_consulted?: string[];
  warnings?: string[];
  timestamp?: string;
  [key: string]: unknown;
}

export interface ResultEntry {
  action: string;
  timestamp: string;
  scored_jobs?: ScoredJob[];
  skill_triage?: SkillTriageEntry[];
  matching_explanation?: string[];
  job_listings?: Record<string, unknown>[];
  skill_gaps?: SkillGap[];
  upskilling_roadmap?: UpskillingItem[];
  salary_insights?: SalaryInsights | null;
  industry_trends?: string[];
  market_outlook?: string | null;
  draft_pitches?: Record<string, unknown>[];
  final_pitch?: string | null;
  summary?: string | null;
  resume_info?: Record<string, unknown> | null;
  resume_debiased?: Record<string, unknown> | null;
  parsing_confidence?: number | null;
  missing_fields?: string[];
  explainability_trace?: ExplainabilityTrace[] | ExplainabilityTrace | null;
  decision_log?: DecisionLogEntry[];
  [key: string]: unknown;
}

export interface PipelineResults {
  session_id: string;
  status: string;
  last_action?: string;
  resume_info?: Record<string, unknown> | null;
  results: ResultEntry[];
  completed_stages?: string[];
  selected_job?: Record<string, unknown> | null;
  awaiting_cv_confirmation?: boolean;
}