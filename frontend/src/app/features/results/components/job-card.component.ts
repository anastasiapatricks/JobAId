import { Component, Input } from '@angular/core';
import { MatCardModule } from '@angular/material/card';
import { MatChipsModule } from '@angular/material/chips';
import { MatIconModule } from '@angular/material/icon';
import { ScoreColorPipe } from '../../../shared/pipes/score-color.pipe';
import { ScoredJob } from '../../../core/models/results.model';

@Component({
  selector: 'jobaid-job-card',
  standalone: true,
  imports: [MatCardModule, MatChipsModule, MatIconModule, ScoreColorPipe],
  template: `
    <mat-card class="job-card" appearance="outlined">
      <mat-card-header>
        <div class="header-content">
          <div class="job-info">
            <mat-card-title>{{ job.title }}</mat-card-title>
            <mat-card-subtitle>
              <mat-icon class="inline-icon">business</mat-icon> {{ job.company }}
              @if (job.location) {
                <span class="separator">|</span>
                <mat-icon class="inline-icon">location_on</mat-icon> {{ job.location }}
              }
            </mat-card-subtitle>
          </div>
          <div class="score-badge" [class]="job.score | scoreColor">
            {{ job.score }}%
          </div>
        </div>
      </mat-card-header>
      <mat-card-content>
        @if (job.explanation) {
          <p class="explanation">{{ job.explanation }}</p>
        }
        @if (job.keywords?.length) {
          <div class="keywords">
            <mat-chip-set>
              @for (keyword of job.keywords!; track keyword) {
                <mat-chip>{{ keyword }}</mat-chip>
              }
            </mat-chip-set>
          </div>
        }
      </mat-card-content>
      @if (job.url) {
        <mat-card-actions>
          <a [href]="job.url" target="_blank" rel="noopener" class="job-link">
            View posting <mat-icon class="inline-icon">open_in_new</mat-icon>
          </a>
        </mat-card-actions>
      }
    </mat-card>
  `,
  styles: `
    :host { display: block; width: 100%; }
    .job-card {
      margin-bottom: 12px;
    }
    .header-content {
      display: flex;
      justify-content: space-between;
      align-items: flex-start;
      width: 100%;
    }
    .job-info {
      flex: 1;
    }
    .score-badge {
      font-size: 1.1rem;
      font-weight: 700;
      padding: 6px 14px;
      border-radius: 20px;
      text-align: center;
      flex-shrink: 0;
      margin-left: 12px;
    }
    .inline-icon {
      font-size: 16px;
      width: 16px;
      height: 16px;
      vertical-align: text-bottom;
    }
    .separator {
      margin: 0 6px;
      opacity: 0.4;
    }
    .explanation {
      margin: 8px 0;
      font-size: 0.9rem;
      line-height: 1.5;
    }
    .keywords {
      margin-top: 8px;
    }
    .job-link {
      display: inline-flex;
      align-items: center;
      gap: 4px;
      color: var(--mat-sys-primary);
      text-decoration: none;
      font-size: 0.9rem;
    }
    .job-link:hover {
      text-decoration: underline;
    }
  `,
})
export class JobCardComponent {
  @Input({ required: true }) job!: ScoredJob;
}
