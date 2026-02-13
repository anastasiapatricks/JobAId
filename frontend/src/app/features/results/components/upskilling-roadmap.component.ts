import { Component, Input } from '@angular/core';
import { MatCardModule } from '@angular/material/card';
import { MatIconModule } from '@angular/material/icon';
import { MatListModule } from '@angular/material/list';
import { UpskillingItem } from '../../../core/models/results.model';

@Component({
  selector: 'jobaid-upskilling-roadmap',
  standalone: true,
  imports: [MatCardModule, MatIconModule, MatListModule],
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
          @if (item.recommended_courses.length) {
            <mat-list class="course-list">
              @for (course of item.recommended_courses; track course) {
                <mat-list-item>
                  <mat-icon matListItemIcon>play_circle</mat-icon>
                  <span>{{ course }}</span>
                </mat-list-item>
              }
            </mat-list>
          }
        </mat-card-content>
      </mat-card>
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
      margin-top: 8px;
    }
  `,
})
export class UpskillingRoadmapComponent {
  @Input({ required: true }) roadmap: UpskillingItem[] = [];
}
