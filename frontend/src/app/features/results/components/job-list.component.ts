import { Component, Input } from '@angular/core';
import { MatIconModule } from '@angular/material/icon';
import { JobCardComponent } from './job-card.component';
import { ScoredJob } from '../../../core/models/results.model';

@Component({
  selector: 'jobaid-job-list',
  standalone: true,
  imports: [JobCardComponent, MatIconModule],
  template: `
    <div class="section-header">
      <mat-icon>work</mat-icon>
      <h3>Job Matches ({{ jobs.length }})</h3>
    </div>
    @for (job of jobs; track job.title + job.company) {
      <jobaid-job-card [job]="job"></jobaid-job-card>
    }
    @empty {
      <p class="empty">No job matches found.</p>
    }
  `,
  styles: `
    .section-header {
      display: flex;
      align-items: center;
      gap: 8px;
      margin-bottom: 12px;
      h3 { margin: 0; }
      mat-icon { color: var(--mat-sys-primary); }
    }
    .empty {
      opacity: 0.6;
      font-style: italic;
    }
  `,
})
export class JobListComponent {
  @Input({ required: true }) jobs: ScoredJob[] = [];
}
