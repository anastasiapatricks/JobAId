import { Component, Input, OnChanges } from '@angular/core';
import { MatCardModule } from '@angular/material/card';
import { MatIconModule } from '@angular/material/icon';
import { marked } from 'marked';
import { DomSanitizer, SafeHtml } from '@angular/platform-browser';

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
        <div class="summary-text" [innerHTML]="renderedHtml"></div>
      </mat-card-content>
    </mat-card>
  `,
  styles: `
    :host { display: block; width: 100%; }
    .summary-card {
      margin-bottom: 16px;
    }
    mat-icon[mat-card-avatar] {
      color: var(--mat-sys-primary);
    }
    .summary-text {
      line-height: 1.6;
    }
    .summary-text ::ng-deep h1,
    .summary-text ::ng-deep h2,
    .summary-text ::ng-deep h3 {
      margin-top: 1em;
      margin-bottom: 0.5em;
    }
    .summary-text ::ng-deep h1 { font-size: 1.3em; }
    .summary-text ::ng-deep h2 { font-size: 1.15em; }
    .summary-text ::ng-deep h3 { font-size: 1.05em; }
    .summary-text ::ng-deep ul,
    .summary-text ::ng-deep ol {
      padding-left: 1.5em;
      margin: 0.4em 0;
    }
    .summary-text ::ng-deep p {
      margin: 0.4em 0;
    }
    .summary-text ::ng-deep strong {
      font-weight: 600;
    }
  `,
})
export class SummaryCardComponent implements OnChanges {
  @Input({ required: true }) summary = '';
  renderedHtml: SafeHtml = '';

  constructor(private sanitizer: DomSanitizer) {}

  ngOnChanges(): void {
    const raw = marked.parse(this.summary, { async: false }) as string;
    this.renderedHtml = this.sanitizer.bypassSecurityTrustHtml(raw);
  }
}
