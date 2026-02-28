import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { SessionCreateRequest, SessionCreateResponse, SessionInfo } from '../models/session.model';
import { PipelineRunRequest, PipelineRunResponse, PipelineStatusResponse, StepResponse } from '../models/pipeline.model';
import { PipelineResults } from '../models/results.model';
import { ResumeUploadResponse } from '../models/resume.model';

@Injectable({ providedIn: 'root' })
export class ApiService {
  private readonly http = inject(HttpClient);

  healthCheck(): Observable<{ status: string; version: string }> {
    return this.http.get<{ status: string; version: string }>('/api/health');
  }

  createSession(body: SessionCreateRequest = {}): Observable<SessionCreateResponse> {
    return this.http.post<SessionCreateResponse>('/api/sessions', body);
  }

  getSession(sessionId: string): Observable<SessionInfo> {
    return this.http.get<SessionInfo>(`/api/sessions/${sessionId}`);
  }

  deleteSession(sessionId: string): Observable<{ message: string }> {
    return this.http.delete<{ message: string }>(`/api/sessions/${sessionId}`);
  }

  uploadResume(sessionId: string, file: File): Observable<ResumeUploadResponse> {
    const formData = new FormData();
    formData.append('file', file);
    return this.http.post<ResumeUploadResponse>(`/api/sessions/${sessionId}/resume`, formData);
  }

  runPipeline(sessionId: string, body: PipelineRunRequest): Observable<PipelineRunResponse> {
    return this.http.post<PipelineRunResponse>(`/api/sessions/${sessionId}/run`, body);
  }

  getStatus(sessionId: string): Observable<PipelineStatusResponse> {
    return this.http.get<PipelineStatusResponse>(`/api/sessions/${sessionId}/status`);
  }

  getResults(sessionId: string): Observable<PipelineResults> {
    return this.http.get<PipelineResults>(`/api/sessions/${sessionId}/results`);
  }

  sendStep(sessionId: string, message: string): Observable<StepResponse> {
    return this.http.post<StepResponse>(`/api/sessions/${sessionId}/step`, { message });
  }

  approve(sessionId: string, approved = true, feedback?: string): Observable<{ session_id: string; approved: boolean }> {
    return this.http.post<{ session_id: string; approved: boolean }>(
      `/api/sessions/${sessionId}/approve`,
      { approved, feedback },
    );
  }
}
