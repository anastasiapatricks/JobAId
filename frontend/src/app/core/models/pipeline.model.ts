export enum PipelineStage {
  Intake = 'intake',
  Parsing = 'parsing',
  ParsingReview = 'parsing_review',
  Discovery = 'discovery',
  DiscoveryReview = 'discovery_review',
  MarketIntel = 'market_intel',
  Pitching = 'pitching',
  PitchReview = 'pitch_review',
  Summarizing = 'summarizing',
  Complete = 'complete',
  Error = 'error',
}

export const PIPELINE_DISPLAY_STAGES: { stage: PipelineStage; label: string }[] = [
  { stage: PipelineStage.Parsing, label: 'Parsing Resume' },
  { stage: PipelineStage.Discovery, label: 'Finding Jobs' },
  { stage: PipelineStage.MarketIntel, label: 'Market Analysis' },
  { stage: PipelineStage.Pitching, label: 'Generating Pitch' },
  { stage: PipelineStage.Summarizing, label: 'Summarizing' },
];

export interface PipelineStatusResponse {
  session_id: string;
  status: string;
  current_stage: string | null;
  iteration_count: number;
  errors: Record<string, unknown>[];
}

export interface PipelineRunRequest {
  resume_text: string;
  job_query: string;
  location_preference?: string;
}

export interface PipelineRunResponse {
  session_id: string;
  status: string;
}

export interface StepResponse {
  session_id: string;
  status: string;
  response_text: string;
  action: string;
}
