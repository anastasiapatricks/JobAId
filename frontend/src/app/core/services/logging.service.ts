import { Injectable, inject, OnDestroy } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { SessionService } from './session.service';

interface LogEntry {
  level: 'info' | 'warn' | 'error';
  message: string;
  context?: Record<string, unknown>;
  timestamp: string;
  session_id: string | null;
}

@Injectable({ providedIn: 'root' })
export class LoggingService implements OnDestroy {
  private readonly http = inject(HttpClient);
  private readonly session = inject(SessionService);

  private buffer: LogEntry[] = [];
  private flushTimer: ReturnType<typeof setInterval>;
  private readonly MAX_BUFFER = 20;
  private readonly FLUSH_INTERVAL = 5000;

  constructor() {
    this.flushTimer = setInterval(() => this.flush(), this.FLUSH_INTERVAL);

    if (typeof window !== 'undefined') {
      window.addEventListener('beforeunload', () => this.flushBeacon());
    }
  }

  ngOnDestroy(): void {
    clearInterval(this.flushTimer);
    this.flush();
  }

  info(message: string, context?: Record<string, unknown>): void {
    this.push('info', message, context);
  }

  warn(message: string, context?: Record<string, unknown>): void {
    this.push('warn', message, context);
  }

  error(message: string, context?: Record<string, unknown>): void {
    this.push('error', message, context);
  }

  private push(level: LogEntry['level'], message: string, context?: Record<string, unknown>): void {
    this.buffer.push({
      level,
      message: message.slice(0, 1000),
      context,
      timestamp: new Date().toISOString(),
      session_id: this.session.currentSessionId(),
    });

    if (this.buffer.length >= this.MAX_BUFFER) {
      this.flush();
    }
  }

  private flush(): void {
    if (this.buffer.length === 0) return;

    const entries = this.buffer.splice(0, this.MAX_BUFFER);
    this.http.post('/api/telemetry', { entries }).subscribe({
      error: () => {
        // Silently drop — don't log to avoid infinite loop
      },
    });
  }

  private flushBeacon(): void {
    if (this.buffer.length === 0) return;

    const entries = this.buffer.splice(0, this.MAX_BUFFER);
    const blob = new Blob([JSON.stringify({ entries })], { type: 'application/json' });
    navigator.sendBeacon('/api/telemetry', blob);
  }
}
