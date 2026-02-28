export interface SessionCreateRequest {
  resume_text?: string;
  job_query?: string;
  location_preference?: string;
}

export interface SessionCreateResponse {
  session_id: string;
  status: string;
}

export interface SessionInfo {
  session_id: string;
  status: string;
}
