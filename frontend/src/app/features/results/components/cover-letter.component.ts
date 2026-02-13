import { Component, Input } from '@angular/core';
import { MatCardModule } from '@angular/material/card';
import { MatIconModule } from '@angular/material/icon';
import { CopyButtonComponent } from '../../../shared/components/copy-button.component';

@Component({
  selector: 'jobaid-cover-letter',
  standalone: true,
  imports: [MatCardModule, MatIconModule, CopyButtonComponent],
  template: `
    <div class="section-header">
      <mat-icon>edit_note</mat-icon>
      <h3>Cover Letter / Pitch</h3>
      <jobaid-copy-button [text]="pitch" class="copy-action"></jobaid-copy-button>
    </div>
    <mat-card appearance="outlined" class="pitch-card">
      <mat-card-content>
        <div class="pitch-text">{{ pitch }}</div>
      </mat-card-content>
    </mat-card>
  `,
  styles: `
    :host { display: block; width: 100%; }
    .section-header {
      display: flex;
      align-items: center;
      gap: 8px;
      margin-bottom: 12px;
      h3 { margin: 0; flex: 1; }
      mat-icon { color: var(--mat-sys-primary); }
    }
    .copy-action {
      flex-shrink: 0;
    }
    .pitch-card {
      margin-bottom: 16px;
    }
    .pitch-text {
      white-space: pre-wrap;
      line-height: 1.7;
      font-size: 0.95rem;
    }
  `,
})
export class CoverLetterComponent {
  @Input({ required: true }) pitch = '';
}
