import { Component, Input } from '@angular/core';
import { MatExpansionModule } from '@angular/material/expansion';
import { MatIconModule } from '@angular/material/icon';
import { DecisionLogEntry } from '../../../core/models/results.model';

@Component({
  selector: 'jobaid-decision-log',
  standalone: true,
  imports: [MatExpansionModule, MatIconModule],
  template: `
    <mat-expansion-panel class="decision-log">
      <mat-expansion-panel-header>
        <mat-panel-title>
          <mat-icon>history</mat-icon>
          Decision Log ({{ entries.length }} entries)
        </mat-panel-title>
      </mat-expansion-panel-header>
      <div class="log-entries">
        @for (entry of entries; track $index) {
          <div class="log-entry">
            <div class="entry-header">
              <span class="stage-tag">{{ entry.stage }}</span>
              <strong>{{ entry.action }}</strong>
              @if (entry.timestamp) {
                <span class="timestamp">{{ entry.timestamp }}</span>
              }
            </div>
            <p class="reasoning">{{ entry.reasoning }}</p>
          </div>
        }
      </div>
    </mat-expansion-panel>
  `,
  styles: `
    .decision-log {
      margin-bottom: 16px;
    }
    mat-panel-title {
      display: flex;
      align-items: center;
      gap: 8px;
      mat-icon { color: var(--mat-sys-primary); }
    }
    .log-entries {
      max-height: 400px;
      overflow-y: auto;
    }
    .log-entry {
      padding: 10px 0;
      border-bottom: 1px solid rgba(0, 0, 0, 0.06);
    }
    .log-entry:last-child {
      border-bottom: none;
    }
    .entry-header {
      display: flex;
      align-items: center;
      gap: 8px;
      flex-wrap: wrap;
    }
    .stage-tag {
      font-size: 0.7rem;
      font-weight: 600;
      text-transform: uppercase;
      padding: 2px 8px;
      border-radius: 4px;
      background: rgba(0, 0, 0, 0.06);
    }
    .timestamp {
      font-size: 0.75rem;
      opacity: 0.5;
      margin-left: auto;
    }
    .reasoning {
      margin: 6px 0 0;
      font-size: 0.85rem;
      opacity: 0.8;
      line-height: 1.4;
    }
  `,
})
export class DecisionLogComponent {
  @Input({ required: true }) entries: DecisionLogEntry[] = [];
}
