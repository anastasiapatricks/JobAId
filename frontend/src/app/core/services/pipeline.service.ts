import { Injectable, inject, signal } from '@angular/core';
import { Subject, interval, switchMap, takeUntil, tap, catchError, EMPTY, filter } from 'rxjs';
import { ApiService } from './api.service';
import { PipelineStatusResponse, PipelineRunRequest } from '../models/pipeline.model';
import { PipelineResults } from '../models/results.model';

@Injectable({ providedIn: 'root' })
export class PipelineService {
  private readonly api = inject(ApiService);
  private readonly stop$ = new Subject<void>();

  readonly pipelineStatus = signal<PipelineStatusResponse | null>(null);
  readonly results = signal<PipelineResults | null>(null);
  readonly isRunning = signal(false);
  readonly error = signal<string | null>(null);

  private onStageChange?: (status: PipelineStatusResponse) => void;
  private onComplete?: (results: PipelineResults) => void;
  private onError?: (error: string) => void;

  startPipeline(
    sessionId: string,
    request: PipelineRunRequest,
    callbacks: {
      onStageChange?: (status: PipelineStatusResponse) => void;
      onComplete?: (results: PipelineResults) => void;
      onError?: (error: string) => void;
    } = {},
  ): void {
    this.onStageChange = callbacks.onStageChange;
    this.onComplete = callbacks.onComplete;
    this.onError = callbacks.onError;
    this.error.set(null);
    this.results.set(null);
    this.isRunning.set(true);

    this.api.runPipeline(sessionId, request).subscribe({
      next: () => this.pollStatus(sessionId),
      error: (err) => {
        const msg = err?.error?.detail || 'Failed to start pipeline';
        this.error.set(msg);
        this.isRunning.set(false);
        this.onError?.(msg);
      },
    });
  }

  private pollStatus(sessionId: string): void {
    let lastStage: string | null = null;

    interval(2000)
      .pipe(
        takeUntil(this.stop$),
        switchMap(() =>
          this.api.getStatus(sessionId).pipe(
            catchError(() => {
              this.error.set('Lost connection to backend');
              this.isRunning.set(false);
              this.stop$.next();
              this.onError?.('Lost connection to backend');
              return EMPTY;
            }),
          ),
        ),
        tap((status) => {
          this.pipelineStatus.set(status);

          if (status.current_stage && status.current_stage !== lastStage) {
            lastStage = status.current_stage;
            this.onStageChange?.(status);
          }
        }),
        filter((status) => status.status === 'complete' || status.status === 'error'),
      )
      .subscribe((status) => {
        this.stop$.next();
        this.isRunning.set(false);

        if (status.status === 'error') {
          const msg = status.errors?.[0]?.['message'] as string || 'Pipeline failed';
          this.error.set(msg);
          this.onError?.(msg);
          return;
        }

        this.api.getResults(sessionId).subscribe({
          next: (results) => {
            this.results.set(results);
            this.onComplete?.(results);
          },
          error: () => {
            this.error.set('Failed to fetch results');
            this.onError?.('Failed to fetch results');
          },
        });
      });
  }

  stopPolling(): void {
    this.stop$.next();
    this.isRunning.set(false);
  }
}
