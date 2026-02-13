import { Component, Input } from '@angular/core';
import { MatCardModule } from '@angular/material/card';
import { MatIconModule } from '@angular/material/icon';

@Component({
  selector: 'jobaid-summary-card',
  standalone: true,
  imports: [MatCardModule, MatIconModule],
  template: `
    <mat-card class="summary-card" appearance="outlined">
      <mat-card-header>
        <mat-icon mat-card-avatar>summarize</mat-icon>
        <mat-card-title>Executive Summary</mat-card-title>
      </mat-card-header>
      <mat-card-content>
        <p class="summary-text">{{ summary }}</p>
      </mat-card-content>
    </mat-card>
  `,
  styles: `
    .summary-card {
      margin-bottom: 16px;
    }
    mat-icon[mat-card-avatar] {
      color: var(--mat-sys-primary);
    }
    .summary-text {
      white-space: pre-wrap;
      line-height: 1.6;
      margin: 0;
    }
  `,
})
export class SummaryCardComponent {
  @Input({ required: true }) summary = '';
}
