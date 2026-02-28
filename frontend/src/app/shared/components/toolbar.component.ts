import { Component, inject } from '@angular/core';
import { TitleCasePipe } from '@angular/common';
import { MatToolbarModule } from '@angular/material/toolbar';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatTooltipModule } from '@angular/material/tooltip';
import { SessionService } from '../../core/services/session.service';
import { ChatService } from '../../core/services/chat.service';
import { PipelineService } from '../../core/services/pipeline.service';

@Component({
  selector: 'jobaid-toolbar',
  standalone: true,
  imports: [TitleCasePipe, MatToolbarModule, MatButtonModule, MatIconModule, MatTooltipModule],
  template: `
    <mat-toolbar color="primary" class="toolbar">
      <mat-icon class="logo-icon">work</mat-icon>
      <span class="logo-text">JobAId</span>
      <span class="spacer"></span>
      @if (session.hasSession()) {
        <span class="session-status">{{ session.sessionStatus() | titlecase }}</span>
      }
      <button
        mat-icon-button
        matTooltip="New Session"
        aria-label="Start new session"
        (click)="onNewSession()"
        [disabled]="pipeline.isRunning()"
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
    }
    .logo-icon {
      margin-right: 8px;
    }
    .logo-text {
      font-weight: 500;
      font-size: 1.25rem;
    }
    .spacer {
      flex: 1;
    }
    .session-status {
      font-size: 0.8rem;
      opacity: 0.8;
      margin-right: 12px;
      padding: 4px 12px;
      border-radius: 12px;
      background: rgba(255, 255, 255, 0.15);
    }
  `,
})
export class ToolbarComponent {
  protected readonly session = inject(SessionService);
  protected readonly pipeline = inject(PipelineService);
  private readonly chat = inject(ChatService);

  onNewSession(): void {
    this.pipeline.stopPolling();
    this.session.clear();
    this.chat.clear();
    this.chat.addWelcome();
  }
}
