import { Component, Input, OnChanges } from '@angular/core';
import { MatTabsModule } from '@angular/material/tabs';
import { PipelineResults, ResultEntry } from '../../core/models/results.model';
import { SummaryCardComponent } from './components/summary-card.component';
import { JobListComponent } from './components/job-list.component';
import { SkillGapsComponent } from './components/skill-gaps.component';
import { UpskillingRoadmapComponent } from './components/upskilling-roadmap.component';
import { SalaryInsightsComponent } from './components/salary-insights.component';
import { CoverLetterComponent } from './components/cover-letter.component';

@Component({
  selector: 'jobaid-results-container',
  standalone: true,
  imports: [
    MatTabsModule,
    SummaryCardComponent,
    JobListComponent,
    SkillGapsComponent,
    UpskillingRoadmapComponent,
    SalaryInsightsComponent,
    CoverLetterComponent,
  ],
  template: `
    @if (entry) {
      <mat-tab-group class="results-tabs" dynamicHeight>
        <mat-tab label="Overview">
          <div class="results-container">
            @if (show('summary') && entry.summary) {
              <jobaid-summary-card [summary]="entry.summary" />
            }

            @if (show('scored_jobs') && entry.scored_jobs?.length) {
              <jobaid-job-list
                [jobs]="entry.scored_jobs!"
                [triage]="entry.skill_triage || []"
              />
            }

            @if (show('skill_gaps') && entry.skill_gaps?.length) {
              <jobaid-skill-gaps [skillGaps]="entry.skill_gaps!" />
            }

            @if (show('upskilling_roadmap') && entry.upskilling_roadmap?.length) {
              <jobaid-upskilling-roadmap [roadmap]="entry.upskilling_roadmap!" />
            }

            @if (show('salary_insights') && (entry.salary_insights || entry.market_outlook)) {
              <jobaid-salary-insights
                [salary]="entry.salary_insights || null"
                [marketOutlook]="entry.market_outlook || ''"
              />
            }

            @if (show('final_pitch') && entry.final_pitch) {
              <jobaid-cover-letter [pitch]="entry.final_pitch" />
            }
          </div>
        </mat-tab>

      </mat-tab-group>
    }
  `,
  styles: [`
    :host {
      display: block;
      width: 100%;
    }

    .results-tabs {
      width: 100%;
    }

    .results-container {
      display: flex;
      flex-direction: column;
      gap: 16px;
      width: 100%;
      padding-top: 12px;
    }
  `],
})
export class ResultsContainerComponent implements OnChanges {
  @Input({ required: true }) results!: PipelineResults;
  @Input() action = '';

  entry: ResultEntry | null = null;

  private static ACTION_SECTIONS: Record<string, string[]> = {
    discovery: ['scored_jobs'],
    market_intel: ['skill_gaps', 'upskilling_roadmap', 'salary_insights', 'market_outlook', 'industry_trends'],
    pitching: ['skill_gaps', 'upskilling_roadmap', 'salary_insights', 'market_outlook', 'final_pitch'],
    summarizing: ['summary'],
  };

  ngOnChanges(): void {
    this.entry = this.getLatestEntry();
  }

  private getLatestEntry(): ResultEntry | null {
    if (!this.results?.results?.length) return null;

    const arr = this.results.results;

    if (this.action) {
      let entry: ResultEntry | null = null;

      for (let i = arr.length - 1; i >= 0; i--) {
        if (arr[i].action === this.action) {
          entry = { ...arr[i] };
          break;
        }
      }

      if (this.action === 'pitching' && entry) {
        for (let i = arr.length - 1; i >= 0; i--) {
          if (arr[i].action === 'market_intel') {
            const mi = arr[i];
            if (!entry.skill_gaps && mi.skill_gaps) entry.skill_gaps = mi.skill_gaps;
            if (!entry.upskilling_roadmap && mi.upskilling_roadmap) entry.upskilling_roadmap = mi.upskilling_roadmap;
            if (!entry.salary_insights && mi.salary_insights) entry.salary_insights = mi.salary_insights;
            if (!entry.market_outlook && mi.market_outlook) entry.market_outlook = mi.market_outlook;
            break;
          }
        }
      }

      return entry;
    }

    return arr[arr.length - 1];
  }

  show(section: string): boolean {
    if (!this.action) return true;
    const allowed = ResultsContainerComponent.ACTION_SECTIONS[this.action];
    return !allowed || allowed.includes(section);
  }

}