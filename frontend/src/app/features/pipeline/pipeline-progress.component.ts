import { Component, Input, computed } from '@angular/core';
import { MatStepperModule } from '@angular/material/stepper';
import { MatIconModule } from '@angular/material/icon';
import { PIPELINE_DISPLAY_STAGES, PipelineStage } from '../../core/models/pipeline.model';

const STAGE_ORDER: string[] = [
  PipelineStage.Parsing,
  PipelineStage.ParsingReview,
  PipelineStage.Discovery,
  PipelineStage.DiscoveryReview,
  PipelineStage.MarketIntel,
  PipelineStage.Pitching,
  PipelineStage.PitchReview,
  PipelineStage.Summarizing,
  PipelineStage.Complete,
];

@Component({
  selector: 'jobaid-pipeline-progress',
  standalone: true,
  imports: [MatStepperModule, MatIconModule],
  template: `
    <div class="progress-container">
      <div class="stage-track">
        @for (stage of displayStages; track stage.stage; let i = $index) {
          <div class="stage-item" [class.active]="isActive(stage.stage)" [class.completed]="isCompleted(stage.stage)">
            <div class="stage-circle">
              @if (isCompleted(stage.stage)) {
                <mat-icon class="done-icon">check</mat-icon>
              } @else {
                <span>{{ i + 1 }}</span>
              }
            </div>
            <span class="stage-label">{{ stage.label }}</span>
          </div>
          @if (i < displayStages.length - 1) {
            <div class="stage-connector" [class.completed]="isCompleted(stage.stage)"></div>
          }
        }
      </div>
    </div>
  `,
  styles: `
    .progress-container {
      padding: 16px 8px;
      overflow-x: auto;
    }
    .stage-track {
      display: flex;
      align-items: center;
      min-width: fit-content;
    }
    .stage-item {
      display: flex;
      flex-direction: column;
      align-items: center;
      gap: 6px;
      min-width: 80px;
    }
    .stage-circle {
      width: 32px;
      height: 32px;
      border-radius: 50%;
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 0.8rem;
      font-weight: 500;
      background: rgba(0, 0, 0, 0.08);
      color: rgba(0, 0, 0, 0.5);
      transition: all 0.3s ease;
    }
    .active .stage-circle {
      background: var(--mat-sys-primary);
      color: var(--mat-sys-on-primary);
      box-shadow: 0 0 0 4px rgba(var(--mat-sys-primary), 0.2);
      animation: pulse 2s infinite;
    }
    .completed .stage-circle {
      background: #2e7d32;
      color: white;
    }
    .done-icon {
      font-size: 18px;
      width: 18px;
      height: 18px;
    }
    .stage-label {
      font-size: 0.7rem;
      text-align: center;
      opacity: 0.6;
      white-space: nowrap;
    }
    .active .stage-label {
      opacity: 1;
      font-weight: 500;
      color: var(--mat-sys-primary);
    }
    .completed .stage-label {
      opacity: 0.8;
    }
    .stage-connector {
      flex: 1;
      height: 2px;
      min-width: 24px;
      background: rgba(0, 0, 0, 0.12);
      margin: 0 4px;
      margin-bottom: 22px;
      transition: background 0.3s ease;
    }
    .stage-connector.completed {
      background: #2e7d32;
    }
    @keyframes pulse {
      0%, 100% { box-shadow: 0 0 0 0 rgba(103, 80, 164, 0.3); }
      50% { box-shadow: 0 0 0 8px rgba(103, 80, 164, 0); }
    }
  `,
})
export class PipelineProgressComponent {
  @Input() currentStage: string | null = null;
  readonly displayStages = PIPELINE_DISPLAY_STAGES;

  private getStageIndex(stage: string): number {
    return STAGE_ORDER.indexOf(stage);
  }

  isActive(stage: PipelineStage): boolean {
    if (!this.currentStage) return false;
    return this.currentStage === stage ||
      (stage === PipelineStage.Parsing && this.currentStage === PipelineStage.ParsingReview) ||
      (stage === PipelineStage.Discovery && this.currentStage === PipelineStage.DiscoveryReview) ||
      (stage === PipelineStage.Pitching && this.currentStage === PipelineStage.PitchReview);
  }

  isCompleted(stage: PipelineStage): boolean {
    if (!this.currentStage) return false;
    const currentIdx = this.getStageIndex(this.currentStage);
    const stageIdx = this.getStageIndex(stage);
    if (currentIdx < 0 || stageIdx < 0) return false;
    return currentIdx > stageIdx && !this.isActive(stage);
  }
}
