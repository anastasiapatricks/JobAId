import { Injectable, inject, signal, computed } from '@angular/core';
import { ApiService } from './api.service';
import { firstValueFrom } from 'rxjs';

@Injectable({ providedIn: 'root' })
export class SessionService {
  private readonly api = inject(ApiService);

  readonly currentSessionId = signal<string | null>(null);
  readonly sessionStatus = signal<string>('none');
  readonly hasSession = computed(() => this.currentSessionId() !== null);

  async ensureSession(): Promise<string> {
    const existing = this.currentSessionId();
    if (existing) return existing;

    const res = await firstValueFrom(this.api.createSession());
    this.currentSessionId.set(res.session_id);
    this.sessionStatus.set(res.status);
    return res.session_id;
  }

  async newSession(): Promise<string> {
    const res = await firstValueFrom(this.api.createSession());
    this.currentSessionId.set(res.session_id);
    this.sessionStatus.set(res.status);
    return res.session_id;
  }

  updateStatus(status: string): void {
    this.sessionStatus.set(status);
  }

  clear(): void {
    this.currentSessionId.set(null);
    this.sessionStatus.set('none');
  }
}
