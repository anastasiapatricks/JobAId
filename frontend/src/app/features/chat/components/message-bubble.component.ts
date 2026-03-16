import { Component, Input, Output, EventEmitter } from '@angular/core';
import { MatCardModule } from '@angular/material/card';
import { MatIconModule } from '@angular/material/icon';
import { MatButtonModule } from '@angular/material/button';
import { ChatMessage } from '../../../core/services/chat.service';
import { ResumePreviewComponent } from '../../resume/resume-preview.component';
import { PipelineProgressComponent } from '../../pipeline/pipeline-progress.component';
import { ResultsContainerComponent } from '../../results/results-container.component';
import { PIPELINE_DISPLAY_STAGES } from '../../../core/models/pipeline.model';

@Component({
  selector: 'jobaid-message-bubble',
  standalone: true,
  imports: [MatCardModule, MatIconModule, MatButtonModule, ResumePreviewComponent, PipelineProgressComponent, ResultsContainerComponent],
  template: `
    <div class="message" [class.user]="message.sender === 'user'" [class.system]="message.sender === 'system'">
      @if (message.sender === 'system') {
        <div class="avatar">
          <mat-icon>smart_toy</mat-icon>
        </div>
      }

      <div class="message-content">
        @if (message.type === 'results') {
          <div class="results-bubble">
            @if (message.results) {
              <jobaid-results-container [results]="message.results" [action]="message.action ?? ''"></jobaid-results-container>
            }
          </div>
        } @else if (message.type === 'resume') {
          <div class="resume-bubble-container">
            <jobaid-resume-preview
              [resumeText]="message.resumeText || ''"
              [fileName]="message.fileName"
            ></jobaid-resume-preview>
          </div>
        } @else {
          <div class="bubble" [class.wide]="message.type === 'stageUpdate'">
            @switch (message.type) {
              @case ('welcome') {
                <div class="welcome-text">
                  <mat-icon class="welcome-icon">waving_hand</mat-icon>
                  <p>{{ message.text }}</p>
                </div>
              }
              @case ('text') {
                <p class="text-content">{{ message.text }}</p>
                @if (message.suggestions?.length) {
                  <div class="suggestion-chips">
                    @for (suggestion of message.suggestions; track suggestion) {
                      <button mat-stroked-button class="suggestion-chip" (click)="suggestionClicked.emit(suggestion)">
                        <mat-icon>search</mat-icon>
                        {{ suggestion }}
                      </button>
                    }
                  </div>
                }
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
      </div>

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
      background: var(--app-brand);
      color: white;
      box-shadow: 0 4px 12px rgba(37, 99, 235, 0.24);
    }

    .avatar mat-icon {
      font-size: 20px;
      width: 20px;
      height: 20px;
    }

    .user-avatar {
      background: #0f172a;
      color: white;
      box-shadow: none;
    }

    .bubble {
      max-width: 72%;
      padding: 14px 16px;
      border-radius: 18px;
      line-height: 1.55;
      overflow: hidden;
      box-shadow: var(--app-shadow);
    }

    .bubble.wide {
      max-width: 86%;
    }

    .system .bubble {
      background: var(--app-system-bubble);
      border: 1px solid var(--app-border);
      border-radius: 18px 18px 18px 6px;
    }

    .user .bubble {
      background: var(--app-user-bubble);
      color: var(--app-brand-dark);
      border: 1px solid #bfdbfe;
      border-radius: 18px 18px 6px 18px;
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
    }

    .welcome-text p {
      margin: 0;
      white-space: pre-wrap;
    }

    .welcome-icon {
      flex-shrink: 0;
      color: var(--app-brand);
    }

    .error-content {
      display: flex;
      gap: 8px;
      align-items: flex-start;
      color: var(--app-error-text);
    }

    .error-content mat-icon {
      flex-shrink: 0;
    }

    .error-content p {
      margin: 0;
    }
  `,
})
export class MessageBubbleComponent {
  @Input({ required: true }) message!: ChatMessage;
  @Output() suggestionClicked = new EventEmitter<string>();

  protected readonly stages = PIPELINE_DISPLAY_STAGES;

  isCompleted(stage: string): boolean {
    return this.message.completedStages?.includes(stage) ?? false;
  }
}
