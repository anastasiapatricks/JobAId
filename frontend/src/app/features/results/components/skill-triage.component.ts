import { Component, Input } from '@angular/core';
import { DecimalPipe } from '@angular/common';
import { MatChipsModule } from '@angular/material/chips';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressBarModule } from '@angular/material/progress-bar';
import { SkillTriageEntry } from '../../../core/models/results.model';

@Component({
  selector: 'jobaid-skill-triage',
  standalone: true,
  imports: [DecimalPipe, MatChipsModule, MatIconModule, MatProgressBarModule],
  template: `
    <div class="section-header">
      <mat-icon>compare_arrows</mat-icon>
      <h3>Skill Match Triage</h3>
    </div>
    <p class="triage-intro">Quick comparison of your skills against each role's requirements:</p>
    @for (item of triage; track item.title + item.company) {
      <div class="triage-card">
        <div class="triage-header">
          <span class="job-title">{{ item.title }}</span>
          <span class="company">{{ item.company }}</span>
          <span class="ratio" [class.high]="item.match_ratio >= 0.7"
                [class.medium]="item.match_ratio >= 0.4 && item.match_ratio < 0.7"
                [class.low]="item.match_ratio < 0.4">
            {{ (item.match_ratio * 100) | number:'1.0-0' }}% match
          </span>
        </div>
        <mat-progress-bar mode="determinate" [value]="item.match_ratio * 100"
          [color]="item.match_ratio >= 0.7 ? 'primary' : item.match_ratio >= 0.4 ? 'accent' : 'warn'">
        </mat-progress-bar>
        <div class="skills-row">
          @if (item.skills_matched.length) {
            <div class="skill-group matched">
              <span class="label">
                <mat-icon>check_circle</mat-icon> You have:
              </span>
              <mat-chip-set>
                @for (skill of item.skills_matched; track skill) {
                  <mat-chip class="chip-matched">{{ skill }}</mat-chip>
                }
              </mat-chip-set>
            </div>
          }
          @if (item.skills_missing.length) {
            <div class="skill-group missing">
              <span class="label">
                <mat-icon>add_circle_outline</mat-icon> To learn:
              </span>
              <mat-chip-set>
                @for (skill of item.skills_missing; track skill) {
                  <mat-chip class="chip-missing">{{ skill }}</mat-chip>
                }
              </mat-chip-set>
            </div>
          }
        </div>
      </div>
    }
  `,
  styles: `
    :host { display: block; width: 100%; }
    .section-header {
      display: flex;
      align-items: center;
      gap: 8px;
      margin-bottom: 8px;
      h3 { margin: 0; }
      mat-icon { color: var(--mat-sys-primary); }
    }
    .triage-intro {
      font-size: 0.875rem;
      opacity: 0.7;
      margin: 0 0 12px;
    }
    .triage-card {
      border: 1px solid rgba(0, 0, 0, 0.1);
      border-radius: 12px;
      padding: 12px 16px;
      margin-bottom: 10px;
    }
    .triage-header {
      display: flex;
      align-items: center;
      gap: 8px;
      margin-bottom: 8px;
      flex-wrap: wrap;
    }
    .job-title { font-weight: 600; }
    .company { opacity: 0.6; font-size: 0.875rem; }
    .ratio {
      margin-left: auto;
      font-weight: 600;
      font-size: 0.875rem;
      padding: 2px 8px;
      border-radius: 12px;
    }
    .ratio.high { color: #2f9e44; background: #b2f2bb; }
    .ratio.medium { color: #e8590c; background: #ffd8a8; }
    .ratio.low { color: #e03131; background: #ffc9c9; }
    mat-progress-bar { margin-bottom: 10px; border-radius: 4px; }
    .skills-row { display: flex; flex-direction: column; gap: 6px; }
    .skill-group {
      display: flex;
      align-items: center;
      gap: 8px;
      flex-wrap: wrap;
    }
    .label {
      display: flex;
      align-items: center;
      gap: 4px;
      font-size: 0.8rem;
      font-weight: 500;
      min-width: 90px;
      mat-icon { font-size: 16px; width: 16px; height: 16px; }
    }
    .matched .label { color: #2f9e44; }
    .missing .label { color: #e8590c; }
    .chip-matched { --mdc-chip-elevated-container-color: #b2f2bb; font-size: 0.75rem; }
    .chip-missing { --mdc-chip-elevated-container-color: #ffd8a8; font-size: 0.75rem; }
  `,
})
export class SkillTriageComponent {
  @Input({ required: true }) triage: SkillTriageEntry[] = [];
}
