import { Component, Input } from '@angular/core';
import { MatCardModule } from '@angular/material/card';
import { MatIconModule } from '@angular/material/icon';
import { ChatMessage } from '../../../core/services/chat.service';
import { ResumePreviewComponent } from '../../resume/resume-preview.component';
import { PipelineProgressComponent } from '../../pipeline/pipeline-progress.component';
import { ResultsContainerComponent } from '../../results/results-container.component';

@Component({
  selector: 'jobaid-message-bubble',
  standalone: true,
  imports: [MatCardModule, MatIconModule, ResumePreviewComponent, PipelineProgressComponent, ResultsContainerComponent],
  template: `
    <div class="message" [class.user]="message.sender === 'user'" [class.system]="message.sender === 'system'">
      @if (message.sender === 'system') {
        <div class="avatar">
          <mat-icon>smart_toy</mat-icon>
        </div>
      }
      @if (message.type === 'results') {
        <div class="results-bubble">
          @if (message.results) {
            <jobaid-results-container [results]="message.results" [action]="message.action ?? ''"></jobaid-results-container>
          }
        </div>
      } @else {
        <div class="bubble" [class.wide]="message.type === 'stageUpdate' || message.type === 'resume'">
          @switch (message.type) {
            @case ('welcome') {
              <div class="welcome-text">
                <mat-icon class="welcome-icon">waving_hand</mat-icon>
                <p>{{ message.text }}</p>
              </div>
            }
            @case ('text') {
              <p class="text-content">{{ message.text }}</p>
            }
            @case ('resume') {
              <jobaid-resume-preview
                [resumeText]="message.resumeText || ''"
                [fileName]="message.fileName"
              ></jobaid-resume-preview>
            }
            @case ('stageUpdate') {
              @if (message.stageStatus) {
                <jobaid-pipeline-progress [currentStage]="message.stageStatus.current_stage"></jobaid-pipeline-progress>
              }
            }
            @case ('error') {
              <div class="error-content">
                <mat-icon>error_outline</mat-icon>
                <p>{{ message.text }}</p>
              </div>
            }
          }
        </div>
      }
      @if (message.sender === 'user') {
        <div class="avatar user-avatar">
          <mat-icon>person</mat-icon>
        </div>
      }
    </div>
  `,
  styles: `
    .message {
      display: flex;
      gap: 10px;
      margin-bottom: 16px;
      max-width: 100%;
    }
    .message.user {
      justify-content: flex-end;
    }
    .message.system {
      justify-content: flex-start;
    }
    .avatar {
      flex-shrink: 0;
      width: 36px;
      height: 36px;
      border-radius: 50%;
      display: flex;
      align-items: center;
      justify-content: center;
      background: var(--mat-sys-primary);
      color: var(--mat-sys-on-primary);
      mat-icon { font-size: 20px; width: 20px; height: 20px; }
    }
    .user-avatar {
      background: var(--mat-sys-tertiary);
      color: var(--mat-sys-on-tertiary);
    }
    .bubble {
      max-width: 70%;
      padding: 12px 16px;
      border-radius: 18px;
      line-height: 1.5;
      overflow: hidden;
    }
    .bubble.wide {
      max-width: 85%;
    }
    .system .bubble {
      background: var(--mat-sys-surface-container);
      border-radius: 18px 18px 18px 4px;
    }
    .user .bubble {
      background: var(--mat-sys-primary-container);
      color: var(--mat-sys-on-primary-container);
      border-radius: 18px 18px 4px 18px;
    }
    .results-bubble {
      flex: 1;
      min-width: 0;
      padding: 8px 0;
    }
    .text-content {
      margin: 0;
      white-space: pre-wrap;
      word-break: break-word;
    }
    .welcome-text {
      display: flex;
      gap: 10px;
      align-items: flex-start;
      p { margin: 0; white-space: pre-wrap; }
    }
    .welcome-icon {
      flex-shrink: 0;
      color: var(--mat-sys-primary);
    }
    .error-content {
      display: flex;
      gap: 8px;
      align-items: flex-start;
      color: #c62828;
      mat-icon { flex-shrink: 0; }
      p { margin: 0; }
    }
  `,
})
export class MessageBubbleComponent {
  @Input({ required: true }) message!: ChatMessage;
}
