import { Component, Input } from '@angular/core';
import { MatCardModule } from '@angular/material/card';
import { MatIconModule } from '@angular/material/icon';

@Component({
  selector: 'jobaid-resume-preview',
  standalone: true,
  imports: [MatCardModule, MatIconModule],
  template: `
    <mat-card class="resume-preview" appearance="outlined">
      <mat-card-header>
        <mat-icon mat-card-avatar>description</mat-icon>
        <mat-card-title>{{ fileName || 'Resume' }}</mat-card-title>
        <mat-card-subtitle>Uploaded successfully</mat-card-subtitle>
      </mat-card-header>
      <mat-card-content>
        <pre class="resume-text">{{ truncatedText }}</pre>
      </mat-card-content>
    </mat-card>
  `,
  styles: `
    .resume-preview {
      max-width: 100%;
    }
    mat-icon[mat-card-avatar] {
      color: var(--mat-sys-primary);
    }
    .resume-text {
      white-space: pre-wrap;
      word-break: break-word;
      font-size: 0.8rem;
      line-height: 1.4;
      max-height: 200px;
      overflow-y: auto;
      background: rgba(0, 0, 0, 0.03);
      padding: 12px;
      border-radius: 8px;
      margin: 0;
    }
  `,
})
export class ResumePreviewComponent {
  @Input({ required: true }) resumeText = '';
  @Input() fileName?: string;

  get truncatedText(): string {
    if (this.resumeText.length > 500) {
      return this.resumeText.substring(0, 500) + '...';
    }
    return this.resumeText;
  }
}
