import { Component, Input } from '@angular/core';
import { PipelineResults } from '../../core/models/results.model';
import { SummaryCardComponent } from './components/summary-card.component';
import { JobListComponent } from './components/job-list.component';
import { SkillGapsComponent } from './components/skill-gaps.component';
import { UpskillingRoadmapComponent } from './components/upskilling-roadmap.component';
import { SalaryInsightsComponent } from './components/salary-insights.component';
import { CoverLetterComponent } from './components/cover-letter.component';
import { DecisionLogComponent } from './components/decision-log.component';

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
    DecisionLogComponent,
  ],
  template: `
    @if (results) {
      <div class="results-container">
        @if (show('summary') && results.summary) {
          <jobaid-summary-card [summary]="results.summary"></jobaid-summary-card>
        }

        @if (show('scored_jobs') && results.scored_jobs?.length) {
          <jobaid-job-list [jobs]="results.scored_jobs!"></jobaid-job-list>
        }

        @if (show('skill_gaps') && results.skill_gaps?.length) {
          <jobaid-skill-gaps [skillGaps]="results.skill_gaps!"></jobaid-skill-gaps>
        }

        @if (show('upskilling_roadmap') && results.upskilling_roadmap?.length) {
          <jobaid-upskilling-roadmap [roadmap]="results.upskilling_roadmap!"></jobaid-upskilling-roadmap>
        }

        @if (show('salary_insights') && (results.salary_insights || results.market_outlook)) {
          <jobaid-salary-insights [salary]="results.salary_insights ?? null" [marketOutlook]="results.market_outlook ?? null"></jobaid-salary-insights>
        }

        @if (show('final_pitch') && results.final_pitch) {
          <jobaid-cover-letter [pitch]="results.final_pitch"></jobaid-cover-letter>
        }

        @if (show('decision_log') && results.decision_log?.length) {
          <jobaid-decision-log [entries]="results.decision_log!"></jobaid-decision-log>
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
export class ResultsContainerComponent {
  @Input({ required: true }) results!: PipelineResults;
  @Input() action = '';

  private static ACTION_SECTIONS: Record<string, string[]> = {
    discovery: ['scored_jobs'],
    market_intel: ['skill_gaps', 'upskilling_roadmap', 'salary_insights', 'market_outlook', 'industry_trends'],
    pitching: ['final_pitch'],
    summarizing: ['summary'],
  };

  show(section: string): boolean {
    if (!this.action) return true;
    const allowed = ResultsContainerComponent.ACTION_SECTIONS[this.action];
    return !allowed || allowed.includes(section);
  }
}
