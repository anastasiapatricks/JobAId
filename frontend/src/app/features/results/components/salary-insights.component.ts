import { Component, Input } from '@angular/core';
import { MatCardModule } from '@angular/material/card';
import { MatIconModule } from '@angular/material/icon';
import { SalaryInsights } from '../../../core/models/results.model';

@Component({
  selector: 'jobaid-salary-insights',
  standalone: true,
  imports: [MatCardModule, MatIconModule],
  template: `
    @if (marketOutlook) {
      <div class="section-header">
        <mat-icon>trending_up</mat-icon>
        <h3>Market Outlook</h3>
      </div>
      <mat-card appearance="outlined" class="outlook-card">
        <mat-card-content>
          <p class="outlook-text">{{ marketOutlook }}</p>
        </mat-card-content>
      </mat-card>
    }
    <div class="section-header">
      <mat-icon>payments</mat-icon>
      <h3>Salary Insights</h3>
    </div>
    @if (salary) {
      <mat-card appearance="outlined" class="salary-card">
        <mat-card-content>
          @if (salary.experience_level) {
            <p class="level">Experience Level: <strong>{{ salary.experience_level }}</strong></p>
          }
          <div class="salary-bar-container">
            <div class="salary-labels">
              <span class="min">{{ formatSalary(salary.min_salary) }}</span>
              <span class="median">{{ formatSalary(salary.median_salary) }}</span>
              <span class="max">{{ formatSalary(salary.max_salary) }}</span>
            </div>
            <div class="salary-bar">
              <div class="bar-fill"></div>
              @if (salary.median_salary && salary.min_salary && salary.max_salary) {
                <div
                  class="median-marker"
                  [style.left.%]="medianPosition"
                ></div>
              }
            </div>
            <div class="salary-sublabels">
              <span>Min</span>
              <span>Median</span>
              <span>Max</span>
            </div>
          </div>
          <p class="source">Source: {{ salary.source || 'N/A' }} | Currency: {{ salary.currency || 'SGD' }}</p>
        </mat-card-content>
      </mat-card>
    }
  `,
  styles: `
    :host { display: block; width: 100%; }
    .section-header {
      display: flex;
      align-items: center;
      gap: 8px;
      margin-bottom: 12px;
      h3 { margin: 0; }
      mat-icon { color: var(--mat-sys-primary); }
    }
    .outlook-card {
      margin-bottom: 16px;
    }
    .outlook-text {
      margin: 0;
      line-height: 1.5;
    }
    .salary-card {
      margin-bottom: 16px;
    }
    .level {
      margin: 0 0 16px 0;
    }
    .salary-bar-container {
      margin: 16px 0;
    }
    .salary-labels {
      display: flex;
      justify-content: space-between;
      margin-bottom: 6px;
      font-weight: 600;
      font-size: 1rem;
    }
    .salary-bar {
      height: 12px;
      background: linear-gradient(90deg, #e8f5e9, #fff8e1, #ffebee);
      border-radius: 6px;
      position: relative;
    }
    .bar-fill {
      height: 100%;
      border-radius: 6px;
    }
    .median-marker {
      position: absolute;
      top: -4px;
      width: 4px;
      height: 20px;
      background: var(--mat-sys-primary);
      border-radius: 2px;
      transform: translateX(-50%);
    }
    .salary-sublabels {
      display: flex;
      justify-content: space-between;
      margin-top: 4px;
      font-size: 0.75rem;
      opacity: 0.5;
    }
    .source {
      margin: 12px 0 0;
      font-size: 0.8rem;
      opacity: 0.5;
    }
  `,
})
export class SalaryInsightsComponent {
  @Input({ required: true }) salary: SalaryInsights | null = null;
  @Input() marketOutlook: string | null = null;

  get medianPosition(): number {
    if (!this.salary?.min_salary || !this.salary?.max_salary || !this.salary?.median_salary) return 50;
    const range = this.salary.max_salary - this.salary.min_salary;
    if (range === 0) return 50;
    return ((this.salary.median_salary - this.salary.min_salary) / range) * 100;
  }

  formatSalary(value: number | null | undefined): string {
    if (value == null) return 'N/A';
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: this.salary?.currency || 'SGD',
      maximumFractionDigits: 0,
    }).format(value);
  }
}
