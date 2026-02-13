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
        @if (results.summary) {
          <jobaid-summary-card [summary]="results.summary"></jobaid-summary-card>
        }

        @if (results.scored_jobs.length) {
          <jobaid-job-list [jobs]="results.scored_jobs"></jobaid-job-list>
        }

        @if (results.skill_gaps.length) {
          <jobaid-skill-gaps [skillGaps]="results.skill_gaps"></jobaid-skill-gaps>
        }

        @if (results.upskilling_roadmap.length) {
          <jobaid-upskilling-roadmap [roadmap]="results.upskilling_roadmap"></jobaid-upskilling-roadmap>
        }

        @if (results.salary_insights) {
          <jobaid-salary-insights [salary]="results.salary_insights"></jobaid-salary-insights>
        }

        @if (results.final_pitch) {
          <jobaid-cover-letter [pitch]="results.final_pitch"></jobaid-cover-letter>
        }

        @if (results.decision_log.length) {
          <jobaid-decision-log [entries]="results.decision_log"></jobaid-decision-log>
        }
      </div>
    }
  `,
  styles: `
    .results-container {
      display: flex;
      flex-direction: column;
      gap: 8px;
    }
  `,
})
export class ResultsContainerComponent {
  @Input({ required: true }) results!: PipelineResults;
}
