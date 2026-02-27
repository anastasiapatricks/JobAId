import { Component, Input } from '@angular/core';
import { MatCardModule } from '@angular/material/card';
import { MatIconModule } from '@angular/material/icon';
import { UpskillingItem } from '../../../core/models/results.model';

@Component({
  selector: 'jobaid-upskilling-roadmap',
  standalone: true,
  imports: [MatCardModule, MatIconModule],
  template: `
    <div class="section-header">
      <mat-icon>school</mat-icon>
      <h3>Upskilling Roadmap</h3>
    </div>
    @for (item of roadmap; track item.skill) {
      <mat-card class="roadmap-item" appearance="outlined">
        <mat-card-content>
          <div class="item-header">
            <span class="priority-badge">P{{ item.priority }}</span>
            <strong>{{ item.skill }}</strong>
            @if (item.estimated_time) {
              <span class="time-estimate">{{ item.estimated_time }}</span>
            }
          </div>
          @if (item.recommended_courses?.length) {
            <ul class="course-list">
              @for (course of item.recommended_courses!; track course) {
                <li class="course-item">
                  <mat-icon class="course-icon">play_circle</mat-icon>
                  <span class="course-text" [innerHTML]="linkify(course)"></span>
                </li>
              }
            </ul>
          }
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
    .roadmap-item {
      margin-bottom: 10px;
    }
    .item-header {
      display: flex;
      align-items: center;
      gap: 10px;
      flex-wrap: wrap;
    }
    .priority-badge {
      background: var(--mat-sys-primary);
      color: var(--mat-sys-on-primary);
      font-size: 0.75rem;
      font-weight: 600;
      padding: 2px 10px;
      border-radius: 12px;
    }
    .time-estimate {
      font-size: 0.8rem;
      opacity: 0.6;
      margin-left: auto;
    }
    .course-list {
      list-style: none;
      margin: 8px 0 0;
      padding: 0;
    }
    .course-item {
      display: flex;
      align-items: flex-start;
      gap: 8px;
      padding: 4px 0;
    }
    .course-icon {
      flex-shrink: 0;
      font-size: 20px;
      width: 20px;
      height: 20px;
      color: var(--mat-sys-primary);
      margin-top: 2px;
    }
    .course-text {
      word-break: break-word;
      white-space: normal;
      line-height: 1.4;
    }
    .course-text a {
      color: var(--mat-sys-primary);
      text-decoration: underline;
    }
  `,
})
export class UpskillingRoadmapComponent {
  @Input({ required: true }) roadmap: UpskillingItem[] = [];

  linkify(text: string): string {
    const urlPattern = /(https?:\/\/[^\s)<>]+)/g;
    const escaped = text.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
    return escaped.replace(urlPattern, '<a href="$1" target="_blank" rel="noopener noreferrer">$1</a>');
  }
}
