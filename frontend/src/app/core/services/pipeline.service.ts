import { Injectable, inject, signal } from '@angular/core';
import { Subject, interval, switchMap, takeUntil, tap, catchError, EMPTY, filter } from 'rxjs';
import { ApiService } from './api.service';
import { LoggingService } from './logging.service';
import { PipelineStatusResponse, PipelineRunRequest, StepResponse } from '../models/pipeline.model';
import { PipelineResults } from '../models/results.model';

@Injectable({ providedIn: 'root' })
export class PipelineService {
  private readonly api = inject(ApiService);
  private readonly log = inject(LoggingService);
  private readonly stop$ = new Subject<void>();

  readonly pipelineStatus = signal<PipelineStatusResponse | null>(null);
  readonly results = signal<PipelineResults | null>(null);
  readonly isRunning = signal(false);
  readonly error = signal<string | null>(null);

  private onStageChange?: (status: PipelineStatusResponse) => void;
  private onComplete?: (results: PipelineResults) => void;
  private onAwaitingInput?: (results: PipelineResults) => void;
  private onError?: (error: string) => void;

  startPipeline(
    sessionId: string,
    request: PipelineRunRequest,
    callbacks: {
      onStageChange?: (status: PipelineStatusResponse) => void;
      onComplete?: (results: PipelineResults) => void;
      onAwaitingInput?: (results: PipelineResults) => void;
      onError?: (error: string) => void;
    } = {},
  ): void {
    this.onStageChange = callbacks.onStageChange;
    this.onComplete = callbacks.onComplete;
    this.onAwaitingInput = callbacks.onAwaitingInput;
    this.onError = callbacks.onError;
    this.error.set(null);
    this.results.set(null);
    this.isRunning.set(true);

    this.log.info('Pipeline start', { sessionId });

    this.api.runPipeline(sessionId, request).subscribe({
      next: () => this.pollStatus(sessionId),
      error: (err) => {
        const msg = err?.error?.detail || 'Failed to start pipeline';
        this.log.error('Pipeline start failed', { sessionId, error: msg });
        this.error.set(msg);
        this.isRunning.set(false);
        this.onError?.(msg);
      },
    });
  }

  sendStep(
    sessionId: string,
    message: string,
    callbacks: {
      onResponse?: (step: StepResponse) => void;
      onAwaitingInput?: (results: PipelineResults) => void;
      onError?: (error: string) => void;
    } = {},
  ): void {
    this.error.set(null);

    this.api.sendStep(sessionId, message).subscribe({
      next: (stepResponse) => {
        callbacks.onResponse?.(stepResponse);

        if (stepResponse.action === 'chitchat') {
          // No agent running, no need to poll
          return;
        }

        // Agent is running — poll until awaiting_input
        this.isRunning.set(true);
        this.onAwaitingInput = callbacks.onAwaitingInput;
        this.onError = callbacks.onError;
        this.pollStatus(sessionId);
      },
      error: (err) => {
        const msg = err?.error?.detail || 'Failed to send message';
        this.error.set(msg);
        callbacks.onError?.(msg);
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
              this.log.error('Polling connection lost', { sessionId });
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
            this.log.info('Stage transition', { sessionId, stage: status.current_stage });
            this.onStageChange?.(status);
          }
        }),
        filter(
          (status) =>
            status.status === 'complete' ||
            status.status === 'error' ||
            status.status === 'awaiting_input',
        ),
      )
      .subscribe((status) => {
        this.stop$.next();
        this.isRunning.set(false);

        if (status.status === 'error') {
          const msg = (status.errors?.[0]?.['message'] as string) || 'Pipeline failed';
          this.log.error('Pipeline error', { sessionId, error: msg });
          this.error.set(msg);
          this.onError?.(msg);
          return;
        }

        // Fetch latest results for both complete and awaiting_input
        this.api.getResults(sessionId).subscribe({
          next: (results) => {
            this.results.set(results);
            this.log.info('Pipeline complete', { sessionId, status: status.status });
            if (status.status === 'complete') {
              this.onComplete?.(results);
            } else {
              this.onAwaitingInput?.(results);
            }
          },
          error: () => {
            this.log.error('Failed to fetch results', { sessionId });
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
