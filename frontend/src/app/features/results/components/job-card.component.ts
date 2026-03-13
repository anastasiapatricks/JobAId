import { Component, Input } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatCardModule } from '@angular/material/card';
import { MatChipsModule } from '@angular/material/chips';
import { MatIconModule } from '@angular/material/icon';
import { MatButtonModule } from '@angular/material/button';
import { MatTooltipModule } from '@angular/material/tooltip';
import { ScoreColorPipe } from '../../../shared/pipes/score-color.pipe';
import { ScoredJob } from '../../../core/models/results.model';

@Component({
  selector: 'jobaid-job-card',
  standalone: true,
  imports: [
    CommonModule,
    MatCardModule,
    MatChipsModule,
    MatIconModule,
    MatButtonModule,
    MatTooltipModule,
    ScoreColorPipe
  ],
  template: `
    <mat-card class="job-card" appearance="outlined" (click)="openJob($event)">
      <div class="card-header-accent" [class]="job.score | scoreColor"></div>
      <div class="card-inner">
        <mat-card-header>
          <div class="header-main">
            <div class="title-row">
              <mat-card-title class="job-title">
                <a [href]="job.url" target="_blank" rel="noopener" (click)="$event.stopPropagation()">{{ job.title }}</a>
              </mat-card-title>
              <div class="score-container" [class]="job.score | scoreColor" [matTooltip]="'Match Score: ' + job.score + '%'">
                <div class="score-glass">
                  <span class="score-value">{{ job.score }}%</span>
                  <span class="score-label">Match</span>
                </div>
              </div>
            </div>
            <mat-card-subtitle class="job-meta">
              <div class="meta-item">
                <mat-icon>business</mat-icon>
                <span>{{ job.company }}</span>
              </div>
              @if (job.location) {
                <div class="meta-item">
                  <mat-icon>location_on</mat-icon>
                  <span>{{ job.location }}</span>
                </div>
              }
              @if (job.category) {
                <div class="meta-item category">
                  <mat-icon>work_outline</mat-icon>
                  <span>{{ job.category }}</span>
                </div>
              }
            </mat-card-subtitle>
          </div>
        </mat-card-header>

        <mat-card-content>
          @if (job.explanation) {
            <div class="match-explanation">
              <mat-icon class="match-icon">auto_awesome</mat-icon>
              <p>{{ job.explanation }}</p>
            </div>
          }
          
          @if (job.description) {
            <p class="description">{{ job.description }}</p>
          }

          <div class="footer-info">
            @if (job.salary_min || job.salary_max) {
              <div class="salary">
                <mat-icon>payments</mat-icon>
                <span>
                  {{ job.salary_min ? (job.salary_min | number:'1.0-0') : '?' }} - 
                  {{ job.salary_max ? (job.salary_max | number:'1.0-0') : '?' }}
                </span>
              </div>
            }
            @if (job.created_at) {
              <div class="date">
                <mat-icon>calendar_today</mat-icon>
                <span>{{ job.created_at | date:'mediumDate' }}</span>
              </div>
            }
          </div>

          @if (job.keywords?.length) {
            <div class="keywords">
              <mat-chip-set>
                @for (keyword of job.keywords!.slice(0, 5); track keyword) {
                  <mat-chip class="compact-chip">{{ keyword }}</mat-chip>
                }
              </mat-chip-set>
            </div>
          }
        </mat-card-content>

        <mat-card-actions align="end">
          <a mat-stroked-button color="primary" [href]="job.url" target="_blank" rel="noopener" (click)="$event.stopPropagation()">
            View Original Posting
            <mat-icon iconPositionEnd>open_in_new</mat-icon>
          </a>
        </mat-card-actions>
      </div>
    </mat-card>
  `,
  styles: `
    :host { display: block; width: 100%; }
    .job-card {
      margin-bottom: 24px;
      border-radius: 16px;
      cursor: pointer;
      transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
      overflow: hidden;
      border: 1px solid var(--mat-sys-outline-variant);
      background: var(--mat-sys-surface);
      position: relative;
    }
    .job-card:hover {
      transform: translateY(-4px);
      box-shadow: 0 12px 24px rgba(0, 0, 0, 0.12);
      border-color: var(--mat-sys-primary);
    }
    .card-header-accent {
      height: 6px;
      width: 100%;
      &.score-high { background: linear-gradient(90deg, #4caf50, #81c784); }
      &.score-medium { background: linear-gradient(90deg, #ffb300, #ffd54f); }
      &.score-low { background: linear-gradient(90deg, #f44336, #ef5350); }
    }
    .card-inner {
      padding: 12px;
    }
    .header-main {
      width: 100%;
    }
    .title-row {
      display: flex;
      justify-content: space-between;
      align-items: flex-start;
      margin-bottom: 8px;
    }
    .job-title {
      font-size: 1.35rem;
      font-weight: 700;
      line-height: 1.25;
      margin: 0;
      a {
        color: var(--mat-sys-on-surface);
        text-decoration: none;
        transition: color 0.2s ease;
      }
      a:hover {
        color: var(--mat-sys-primary);
      }
    }
    .score-container {
      display: flex;
      flex-direction: column;
      align-items: center;
      min-width: 64px;
      margin-left: 16px;
    }
    .score-glass {
      display: flex;
      flex-direction: column;
      align-items: center;
      padding: 8px 12px;
      border-radius: 12px;
      background: rgba(255, 255, 255, 0.1);
      backdrop-filter: blur(8px);
      border: 1px solid rgba(255, 255, 255, 0.2);
      box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05);

      .score-high & {
        background: rgba(76, 175, 80, 0.15);
        border-color: rgba(76, 175, 80, 0.3);
        color: #2e7d32;
      }
      .score-medium & {
        background: rgba(255, 179, 0, 0.15);
        border-color: rgba(255, 179, 0, 0.3);
        color: #f57f17;
      }
      .score-low & {
        background: rgba(244, 67, 54, 0.15);
        border-color: rgba(244, 67, 54, 0.3);
        color: #c62828;
      }
      
      .dark-theme & {
        .score-high & { color: #81c784; }
        .score-medium & { color: #ffd54f; }
        .score-low & { color: #ef5350; }
      }
    }
    .score-value {
      font-size: 1.2rem;
      font-weight: 800;
    }
    .score-label {
      font-size: 0.65rem;
      text-transform: uppercase;
      letter-spacing: 0.5px;
      font-weight: 600;
      opacity: 0.8;
    }
    .job-meta {
      display: flex;
      flex-wrap: wrap;
      gap: 16px;
      margin-top: 8px;
      color: var(--mat-sys-on-surface-variant);
    }
    .meta-item {
      display: flex;
      align-items: center;
      gap: 6px;
      font-size: 0.9rem;
      mat-icon {
        font-size: 18px;
        width: 18px;
        height: 18px;
        opacity: 0.7;
      }
    }
    .match-explanation {
      display: flex;
      gap: 10px;
      background: var(--mat-sys-primary-container);
      color: var(--mat-sys-on-primary-container);
      padding: 12px 16px;
      border-radius: 12px;
      margin: 20px 0;
      font-size: 0.925rem;
      border-left: 4px solid var(--mat-sys-primary);
      p { margin: 0; line-height: 1.5; }
      .match-icon {
        font-size: 20px;
        width: 20px;
        height: 20px;
        color: var(--mat-sys-primary);
      }
    }
    .description {
      font-size: 0.95rem;
      line-height: 1.6;
      color: var(--mat-sys-on-surface);
      margin: 16px 0;
      display: -webkit-box;
      -webkit-line-clamp: 3;
      -webkit-box-orient: vertical;
      overflow: hidden;
      opacity: 0.9;
    }
    .footer-info {
      display: flex;
      gap: 24px;
      margin: 16px 0;
      padding: 12px 0;
      border-top: 1px solid var(--mat-sys-outline-variant);
      color: var(--mat-sys-on-surface-variant);
      font-size: 0.9rem;
    }
    .salary, .date {
      display: flex;
      align-items: center;
      gap: 8px;
      mat-icon {
        font-size: 18px;
        width: 18px;
        height: 18px;
        opacity: 0.7;
      }
    }
    .keywords {
      margin-top: 16px;
    }
    .compact-chip {
      --mat-chip-container-height: 28px;
      font-size: 0.8rem;
      background: var(--mat-sys-secondary-container) !important;
      color: var(--mat-sys-on-secondary-container) !important;
    }
    mat-card-actions {
      padding: 12px 0 4px;
    }
  `,
})
export class JobCardComponent {
  @Input({ required: true }) job!: ScoredJob;

  openJob(event: MouseEvent): void {
    if (this.job.url) {
      window.open(this.job.url, '_blank', 'noopener');
    }
  }
}
