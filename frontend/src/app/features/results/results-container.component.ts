import { Component, Input, OnChanges } from '@angular/core';
import { PipelineResults, ResultEntry } from '../../core/models/results.model';
import { SummaryCardComponent } from './components/summary-card.component';
import { JobListComponent } from './components/job-list.component';
import { SkillGapsComponent } from './components/skill-gaps.component';
import { UpskillingRoadmapComponent } from './components/upskilling-roadmap.component';
import { SalaryInsightsComponent } from './components/salary-insights.component';
import { CoverLetterComponent } from './components/cover-letter.component';
import { SkillTriageComponent } from './components/skill-triage.component';
@Component({
  selector: 'jobaid-results-container',
  standalone: true,
  imports: [
    SummaryCardComponent,
    JobListComponent,
    SkillGapsComponent,
    UpskillingRoadmapComponent,
    SalaryInsightsComponent,
    CoverLetterComponent,
    SkillTriageComponent,
  ],
  template: `
    @if (entry) {
      <div class="results-container">
        @if (show('summary') && entry.summary) {
          <jobaid-summary-card [summary]="entry.summary"></jobaid-summary-card>
        }

        @if (show('scored_jobs') && entry.scored_jobs?.length) {
          <jobaid-job-list [jobs]="entry.scored_jobs!"></jobaid-job-list>
        }

        @if (show('skill_triage') && entry.skill_triage?.length) {
          <jobaid-skill-triage [triage]="entry.skill_triage!"></jobaid-skill-triage>
        }

        @if (show('skill_gaps') && entry.skill_gaps?.length) {
          <jobaid-skill-gaps [skillGaps]="entry.skill_gaps!"></jobaid-skill-gaps>
        }

        @if (show('upskilling_roadmap') && entry.upskilling_roadmap?.length) {
          <jobaid-upskilling-roadmap [roadmap]="entry.upskilling_roadmap!"></jobaid-upskilling-roadmap>
        }

        @if (show('salary_insights') && (entry.salary_insights || entry.market_outlook)) {
          <jobaid-salary-insights [salary]="entry.salary_insights ?? null" [marketOutlook]="entry.market_outlook ?? null"></jobaid-salary-insights>
        }

        @if (show('final_pitch') && entry.final_pitch) {
          <jobaid-cover-letter [pitch]="entry.final_pitch"></jobaid-cover-letter>
        }
      </div>
    }
  `,
  styles: `
    :host {
      display: block;
      width: 100%;
    }
    .results-container {
      display: flex;
      flex-direction: column;
      gap: 16px;
      width: 100%;
    }
  `,
})
export class ResultsContainerComponent implements OnChanges {
  @Input({ required: true }) results!: PipelineResults;
  @Input() action = '';

  entry: ResultEntry | null = null;

  private static ACTION_SECTIONS: Record<string, string[]> = {
    discovery: ['scored_jobs', 'skill_triage'],
    market_intel: ['skill_gaps', 'upskilling_roadmap', 'salary_insights', 'market_outlook', 'industry_trends'],
    pitching: ['final_pitch'],
    summarizing: ['summary'],
  };

  ngOnChanges(): void {
    this.entry = this.getLatestEntry();
  }

  private getLatestEntry(): ResultEntry | null {
    if (!this.results?.results?.length) return null;

    const arr = this.results.results;
    if (this.action) {
      // Find the last entry matching this action
      for (let i = arr.length - 1; i >= 0; i--) {
        if (arr[i].action === this.action) {
          return arr[i];
        }
      }
    }

    // Fallback: return the last entry
    return arr[arr.length - 1];
  }

  show(section: string): boolean {
    if (!this.action) return true;
    const allowed = ResultsContainerComponent.ACTION_SECTIONS[this.action];
    return !allowed || allowed.includes(section);
  }
}
