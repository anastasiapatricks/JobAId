import { Component, Input } from '@angular/core';
import { MatChipsModule } from '@angular/material/chips';
import { MatIconModule } from '@angular/material/icon';
import { SkillGap } from '../../../core/models/results.model';

@Component({
  selector: 'jobaid-skill-gaps',
  standalone: true,
  imports: [MatChipsModule, MatIconModule],
  template: `
    <div class="section-header">
      <mat-icon>psychology</mat-icon>
      <h3>Skill Gaps</h3>
    </div>
    <div class="chips-container">
      <mat-chip-set>
        @for (gap of skillGaps; track gap.skill) {
          <mat-chip [class]="'importance-' + gap.importance">
            {{ gap.skill }}
            <span class="importance-label">({{ gap.importance }})</span>
          </mat-chip>
        }
      </mat-chip-set>
    </div>
    @if (!skillGaps.length) {
      <p class="empty">No skill gaps identified.</p>
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
    .chips-container {
      margin-bottom: 16px;
    }
    .importance-label {
      font-size: 0.75rem;
      margin-left: 4px;
      opacity: 0.7;
    }
    .empty {
      opacity: 0.6;
      font-style: italic;
    }
  `,
})
export class SkillGapsComponent {
  @Input({ required: true }) skillGaps: SkillGap[] = [];
}
