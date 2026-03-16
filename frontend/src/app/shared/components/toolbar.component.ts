import { Component, inject, computed } from '@angular/core';
import { TitleCasePipe } from '@angular/common';
import { MatToolbarModule } from '@angular/material/toolbar';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatTooltipModule } from '@angular/material/tooltip';
import { RouterLink } from '@angular/router';
import { SessionService } from '../../core/services/session.service';
import { ChatService } from '../../core/services/chat.service';
import { PipelineService } from '../../core/services/pipeline.service';

@Component({
  selector: 'jobaid-toolbar',
  standalone: true,
  imports: [
    TitleCasePipe,
    MatToolbarModule,
    MatButtonModule,
    MatIconModule,
    MatTooltipModule,
    RouterLink,
  ],
  template: `
    <mat-toolbar class="toolbar">
      <a routerLink="/" class="logo-link">
        <mat-icon class="logo-icon">work</mat-icon>
        <span class="logo-text">JobAId</span>
      </a>

      <span class="spacer"></span>

      @if (session.hasSession()) {
        <span
          class="session-status"
          [class.running]="session.sessionStatus() === 'running'"
        >
          @if (session.sessionStatus() === 'running') {
            <mat-icon class="status-icon rotating">sync</mat-icon>
          }
          {{ sessionStatusText() | titlecase }}
        </span>
      }

      <button
        mat-icon-button
        matTooltip="New Session"
        aria-label="Start new session"
        (click)="onNewSession()"
        [disabled]="pipeline.isRunning()"
        class="new-session-btn"
      >
        <mat-icon>add_circle_outline</mat-icon>
      </button>
    </mat-toolbar>
  `,
  styles: `
    .toolbar {
      position: sticky;
      top: 0;
      z-index: 100;

      /* Slightly darker baby blue */
      background: linear-gradient(135deg, #4DA9FF 0%, #22C7E8 100%) !important;

      color: white !important;
      border-bottom: 1px solid rgba(0,0,0,0.05);
      box-shadow: 0 6px 16px rgba(34,199,232,0.25);
    }

    .logo-link {
      display: flex;
      align-items: center;
      text-decoration: none;
      color: white;
      cursor: pointer;
    }

    .logo-icon {
      margin-right: 8px;
      color: white;
    }

    .logo-text {
      font-weight: 600;
      font-size: 1.25rem;
      letter-spacing: 0.2px;
      color: white;
    }

    .spacer {
      flex: 1;
    }

    .session-status {
      font-size: 0.8rem;
      margin-right: 12px;
      padding: 5px 12px;
      border-radius: 14px;

      background: rgba(255,255,255,0.25);
      color: white;

      display: flex;
      align-items: center;
      gap: 6px;

      font-weight: 500;
      transition: all 0.25s ease;

      &.running {
        background: rgba(255,255,255,0.35);
        box-shadow: 0 0 8px rgba(255,255,255,0.4);
      }
    }

    .status-icon {
      font-size: 16px;
      width: 16px;
      height: 16px;
      color: white;
    }

    .new-session-btn {
      color: white !important;
    }

    .new-session-btn:hover {
      background: rgba(255,255,255,0.25);
    }

    .new-session-btn[disabled] {
      opacity: 0.5;
    }

    @keyframes rotate {
      from { transform: rotate(0deg); }
      to { transform: rotate(360deg); }
    }

    .rotating {
      animation: rotate 2s linear infinite;
    }
  `,
})
export class ToolbarComponent {
  protected readonly session = inject(SessionService);
  protected readonly pipeline = inject(PipelineService);
  private readonly chat = inject(ChatService);

  readonly sessionStatusText = computed(() => {
    const s = this.session.sessionStatus();

    if (s === 'running') {
      const stage = this.pipeline.pipelineStatus()?.current_stage;
      if (stage) return stage.replace('_', ' ');
      return 'running';
    }

    if (s === 'awaiting_input') return 'Ready';
    return s;
  });

  onNewSession(): void {
    this.pipeline.stopPolling();
    this.session.clear();
    this.chat.clear();
    this.chat.addWelcome();
  }
}