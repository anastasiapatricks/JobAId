import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatIconModule } from '@angular/material/icon';
import { ChatService } from '../../../core/services/chat.service';
import { PIPELINE_DISPLAY_STAGES } from '../../../core/models/pipeline.model';

@Component({
  selector: 'jobaid-agent-sidebar',
  standalone: true,
  imports: [CommonModule, MatIconModule],
  template: `
    <div class="sidebar-container">
      <div class="sidebar-header">
        <h2>Career Roadmap</h2>
        <p>Your journey with JobAId agents</p>
      </div>

      <div class="agent-list">
        @for (item of stages; track item.stage) {
          <div class="agent-item"
               [class.active]="currentStage() === item.stage"
               [class.completed]="isCompleted(item.stage)">
            
            <div class="status-indicator">
              @if (isCompleted(item.stage)) {
                <mat-icon class="check-icon">check_circle</mat-icon>
              } @else {
                <div class="dot" [class.pulse]="currentStage() === item.stage"></div>
              }
            </div>

            <div class="agent-info">
              <span class="agent-label">{{ item.label }}</span>

              @if (isCompleted(item.stage) || currentStage() === item.stage) {
                <span class="agent-status">
                  {{ isCompleted(item.stage) ? 'Completed' : 'Running' }}
                </span>
              }
            </div>

          </div>
        }
      </div>

      <div class="sidebar-footer">
        <div class="status-badge">
          <div class="pulse-dot"></div>
          System Online
        </div>
      </div>
    </div>
  `,
  styles: `
    :host {
      display: block;
      width: 280px;
      height: 100%;
      background: white;
      border-right: 1px solid #e5e7eb;
      z-index: 10;
    }

    .sidebar-container {
      display: flex;
      flex-direction: column;
      height: 100%;
      padding: 24px 16px;
    }

    .sidebar-header {
      margin-bottom: 32px;
    }

    .sidebar-header h2 {
      margin: 0;
      font-size: 1.25rem;
      font-weight: 600;
      color: #1e3a8a;
    }

    .sidebar-header p {
      margin: 4px 0 0;
      font-size: 0.8rem;
      opacity: 0.7;
    }

    .agent-list {
      display: flex;
      flex-direction: column;
      gap: 16px;
      flex: 1;
    }

    .agent-item {
      display: flex;
      align-items: center;
      gap: 12px;
      padding: 12px;
      border-radius: 12px;
      background: #f8fafc;
      transition: all 0.25s ease;
      border: 1px solid transparent;
    }

    /* ACTIVE AGENT (RUNNING) */
    .agent-item.active {
      background: rgba(77,169,255,0.12);
      border: 1px solid #4DA9FF;
      box-shadow: 0 0 10px rgba(77,169,255,0.25);
      transform: translateX(4px);
    }

    /* COMPLETED AGENT */
    .agent-item.completed {
      background: #f1f5f9;
      opacity: 0.9;
    }

    .status-indicator {
      width: 24px;
      height: 24px;
      display: flex;
      align-items: center;
      justify-content: center;
    }

    .check-icon {
      color: #4DA9FF;
      font-size: 20px;
      width: 20px;
      height: 20px;
    }

    .dot {
      width: 8px;
      height: 8px;
      border-radius: 50%;
      background: #9ca3af;
    }

    .active .dot {
      background: #4DA9FF;
    }

    .agent-info {
      display: flex;
      flex-direction: column;
    }

    .agent-label {
      font-size: 0.9rem;
      font-weight: 500;
    }

    .agent-status {
      font-size: 0.75rem;
      opacity: 0.7;
    }

    /* ACTIVE PULSE ANIMATION */
    .pulse {
      animation: pulse-ring 1.5s ease-out infinite;
    }

    @keyframes pulse-ring {
      0% {
        transform: scale(0.9);
        box-shadow: 0 0 0 0 rgba(77,169,255,0.6);
      }
      70% {
        transform: scale(1);
        box-shadow: 0 0 0 10px rgba(77,169,255,0);
      }
      100% {
        transform: scale(0.9);
      }
    }

    .sidebar-footer {
      margin-top: auto;
      padding-top: 16px;
      border-top: 1px solid #e5e7eb;
    }

    .status-badge {
      display: flex;
      align-items: center;
      gap: 8px;
      font-size: 0.75rem;
      font-weight: 500;
      color: #6b7280;
    }

    .pulse-dot {
      width: 6px;
      height: 6px;
      background: #22c55e;
      border-radius: 50%;
      animation: status-pulse 2s infinite;
    }

    @keyframes status-pulse {
      0% { opacity: 1; }
      50% { opacity: 0.4; }
      100% { opacity: 1; }
    }

    @media (max-width: 900px) {
      :host {
        display: none;
      }
    }
  `,
})
export class AgentSidebarComponent {
  private readonly chat = inject(ChatService);

  protected readonly stages = PIPELINE_DISPLAY_STAGES;
  protected readonly currentStage = this.chat.currentStage;
  protected readonly completedStages = this.chat.completedStages;

  isCompleted(stage: string): boolean {
    return this.completedStages().includes(stage);
  }
}