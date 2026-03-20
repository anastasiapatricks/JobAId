import { Component, inject, computed } from '@angular/core';
import { DecimalPipe, KeyValuePipe, JsonPipe } from '@angular/common';
import { MatCardModule } from '@angular/material/card';
import { MatIconModule } from '@angular/material/icon';
import { MatExpansionModule } from '@angular/material/expansion';
import { MatChipsModule } from '@angular/material/chips';
import { MatDividerModule } from '@angular/material/divider';
import { RouterLink } from '@angular/router';
import { MatButtonModule } from '@angular/material/button';
import { PipelineService } from '../../core/services/pipeline.service';
import { ExplainabilityTrace, DecisionLogEntry, ResultEntry } from '../../core/models/results.model';

interface TraceWithAction {
  action: string;
  timestamp: string;
  trace: ExplainabilityTrace;
}

@Component({
  selector: 'jobaid-explainability-page',
  standalone: true,
  imports: [
    DecimalPipe,
    KeyValuePipe,
    JsonPipe,
    MatCardModule,
    MatIconModule,
    MatExpansionModule,
    MatChipsModule,
    MatDividerModule,
    MatButtonModule,
    RouterLink,
  ],
  template: `
    <div class="xai-page">
      <div class="xai-header">
        <div class="xai-title">
          <mat-icon>psychology</mat-icon>
          <h1>Explainability Log</h1>
        </div>
        <p class="xai-subtitle">
          How each AI agent made its decisions — confidence scores, reasoning, feature attributions, and fairness warnings.
        </p>
        <a mat-stroked-button routerLink="/chat" class="back-btn">
          <mat-icon>arrow_back</mat-icon>
          Back to Chat
        </a>
      </div>

      @if (!hasData()) {
        <div class="empty-state">
          <mat-icon>info_outline</mat-icon>
          <p>No session data yet. Run the pipeline first, then come back here to review the explainability log.</p>
          <a mat-flat-button routerLink="/chat">Go to Chat</a>
        </div>
      } @else {
        <!-- Agent XAI Traces -->
        @if (traces().length) {
          <section class="xai-section">
            <h2 class="section-heading">
              <mat-icon>analytics</mat-icon>
              Agent Traces ({{ traces().length }})
            </h2>

            <mat-accordion multi>
              @for (item of traces(); track item.action + item.timestamp) {
                <mat-expansion-panel class="trace-panel">
                  <mat-expansion-panel-header>
                    <mat-panel-title class="trace-title">
                      <span class="agent-tag">{{ item.trace.agent_name }}</span>
                      <span class="action-label">{{ item.action }}</span>
                    </mat-panel-title>
                    <mat-panel-description class="trace-desc">
                      <span class="confidence-badge" [class]="confidenceClass(item.trace.confidence)">
                        {{ (item.trace.confidence * 100) | number:'1.0-0' }}% confidence
                      </span>
                      @if (item.trace.warnings?.length) {
                        <mat-icon class="warn-icon" matTooltip="Has warnings">warning</mat-icon>
                      }
                    </mat-panel-description>
                  </mat-expansion-panel-header>

                  <div class="trace-body">
                    <!-- Prompt version + timestamp -->
                    <div class="meta-row">
                      <span class="meta-label">Prompt version</span>
                      <code class="meta-value">{{ item.trace.prompt_version }}</code>
                      <span class="meta-label ml">Timestamp</span>
                      <span class="meta-value">{{ formatTs(item.trace.timestamp) }}</span>
                    </div>

                    <mat-divider></mat-divider>

                    <!-- Reasoning -->
                    <div class="trace-block">
                      <div class="block-label">
                        <mat-icon>chat_bubble_outline</mat-icon>
                        Reasoning
                      </div>
                      <p class="block-text">{{ item.trace.reasoning }}</p>
                    </div>

                    <!-- Grounding score -->
                    <div class="trace-block">
                      <div class="block-label">
                        <mat-icon>verified</mat-icon>
                        Grounding Score
                      </div>
                      <div class="score-bar-wrap">
                        <div class="score-bar">
                          <div class="score-fill" [style.width.%]="item.trace.grounding_score * 100"
                               [class]="confidenceClass(item.trace.grounding_score)"></div>
                        </div>
                        <span class="score-label">{{ item.trace.grounding_score | number:'1.2-2' }}</span>
                      </div>
                    </div>

                    <!-- Feature attributions -->
                    @if (hasAttributions(item.trace)) {
                      <div class="trace-block">
                        <div class="block-label">
                          <mat-icon>bar_chart</mat-icon>
                          Feature Attributions
                        </div>
                        <div class="attr-grid">
                          @for (kv of item.trace.feature_attributions | keyvalue; track kv.key) {
                            <div class="attr-entry">
                              <span class="attr-key">{{ kv.key }}</span>
                              <pre class="attr-val">{{ kv.value | json }}</pre>
                            </div>
                          }
                        </div>
                      </div>
                    }

                    <!-- Sources consulted -->
                    @if (item.trace.sources_consulted?.length) {
                      <div class="trace-block">
                        <div class="block-label">
                          <mat-icon>source</mat-icon>
                          Sources Consulted
                        </div>
                        <mat-chip-set>
                          @for (src of item.trace.sources_consulted; track src) {
                            <mat-chip>{{ src }}</mat-chip>
                          }
                        </mat-chip-set>
                      </div>
                    }

                    <!-- Warnings -->
                    @if (item.trace.warnings?.length) {
                      <div class="trace-block warnings-block">
                        <div class="block-label warn-label">
                          <mat-icon>warning</mat-icon>
                          Warnings
                        </div>
                        <ul class="warn-list">
                          @for (w of item.trace.warnings; track w) {
                            <li>{{ w }}</li>
                          }
                        </ul>
                      </div>
                    }
                  </div>
                </mat-expansion-panel>
              }
            </mat-accordion>
          </section>
        }

        <!-- Decision Log -->
        @if (decisionLog().length) {
          <section class="xai-section">
            <h2 class="section-heading">
              <mat-icon>history</mat-icon>
              Orchestrator Decision Log ({{ decisionLog().length }} entries)
            </h2>

            <div class="decision-log">
              @for (entry of decisionLog(); track $index) {
                <div class="decision-entry">
                  <div class="decision-header">
                    <span class="stage-tag">{{ entry.stage }}</span>
                    <strong class="decision-action">{{ entry.action }}</strong>
                    @if (entry.timestamp) {
                      <span class="decision-ts">{{ formatTs(entry.timestamp) }}</span>
                    }
                  </div>
                  @if (entry.reasoning) {
                    <p class="decision-reasoning">{{ entry.reasoning }}</p>
                  }
                </div>
              }
            </div>
          </section>
        }
      }
    </div>
  `,
  styles: `
    .xai-page {
      max-width: 900px;
      margin: 0 auto;
      padding: 24px 16px 48px;
    }

    .xai-header {
      margin-bottom: 32px;
    }

    .xai-title {
      display: flex;
      align-items: center;
      gap: 10px;
      mat-icon {
        font-size: 2rem;
        width: 2rem;
        height: 2rem;
        color: var(--mat-sys-primary);
      }
      h1 {
        margin: 0;
        font-size: 1.75rem;
        font-weight: 600;
      }
    }

    .xai-subtitle {
      margin: 8px 0 16px;
      color: var(--mat-sys-on-surface-variant);
      font-size: 0.95rem;
    }

    .back-btn {
      mat-icon { font-size: 18px; width: 18px; height: 18px; }
    }

    .empty-state {
      text-align: center;
      padding: 48px 16px;
      color: var(--mat-sys-on-surface-variant);
      display: flex;
      flex-direction: column;
      align-items: center;
      gap: 16px;
      mat-icon { font-size: 48px; width: 48px; height: 48px; opacity: 0.4; }
      p { margin: 0; font-size: 1rem; }
    }

    .xai-section {
      margin-bottom: 40px;
    }

    .section-heading {
      display: flex;
      align-items: center;
      gap: 8px;
      font-size: 1.1rem;
      font-weight: 600;
      margin: 0 0 16px;
      color: var(--mat-sys-on-surface);
      mat-icon { color: var(--mat-sys-primary); }
    }

    /* Trace panels */
    .trace-panel {
      margin-bottom: 8px;
    }

    .trace-title {
      display: flex;
      align-items: center;
      gap: 8px;
    }

    .agent-tag {
      font-size: 0.75rem;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0.5px;
      padding: 2px 8px;
      border-radius: 4px;
      background: var(--mat-sys-primary-container);
      color: var(--mat-sys-on-primary-container);
    }

    .action-label {
      font-size: 0.9rem;
      font-weight: 500;
    }

    .trace-desc {
      display: flex;
      align-items: center;
      gap: 8px;
    }

    .confidence-badge {
      font-size: 0.78rem;
      font-weight: 600;
      padding: 2px 8px;
      border-radius: 12px;

      &.high { background: #d4edda; color: #155724; }
      &.mid  { background: #fff3cd; color: #856404; }
      &.low  { background: #f8d7da; color: #721c24; }
    }

    .warn-icon {
      font-size: 18px;
      width: 18px;
      height: 18px;
      color: #e67e22;
    }

    .trace-body {
      padding: 8px 0;
    }

    .meta-row {
      display: flex;
      align-items: center;
      gap: 8px;
      flex-wrap: wrap;
      font-size: 0.8rem;
      padding: 4px 0 12px;
    }

    .meta-label {
      color: var(--mat-sys-on-surface-variant);
      font-weight: 500;
      &.ml { margin-left: 16px; }
    }

    .meta-value {
      font-family: monospace;
      font-size: 0.8rem;
    }

    .trace-block {
      margin: 16px 0;
    }

    .block-label {
      display: flex;
      align-items: center;
      gap: 6px;
      font-size: 0.8rem;
      font-weight: 600;
      text-transform: uppercase;
      letter-spacing: 0.5px;
      color: var(--mat-sys-on-surface-variant);
      margin-bottom: 8px;
      mat-icon { font-size: 16px; width: 16px; height: 16px; }
    }

    .block-text {
      margin: 0;
      font-size: 0.9rem;
      line-height: 1.5;
    }

    .score-bar-wrap {
      display: flex;
      align-items: center;
      gap: 12px;
    }

    .score-bar {
      flex: 1;
      height: 8px;
      border-radius: 4px;
      background: rgba(0,0,0,0.08);
      overflow: hidden;
    }

    .score-fill {
      height: 100%;
      border-radius: 4px;
      transition: width 0.3s ease;
      &.high { background: #28a745; }
      &.mid  { background: #ffc107; }
      &.low  { background: #dc3545; }
    }

    .score-label {
      font-size: 0.85rem;
      font-weight: 600;
      min-width: 36px;
    }

    .attr-grid {
      display: flex;
      flex-direction: column;
      gap: 8px;
    }

    .attr-entry {
      display: flex;
      flex-direction: column;
      gap: 2px;
    }

    .attr-key {
      font-size: 0.8rem;
      font-weight: 600;
      color: var(--mat-sys-on-surface-variant);
    }

    .attr-val {
      margin: 0;
      font-size: 0.78rem;
      font-family: monospace;
      background: rgba(0,0,0,0.04);
      padding: 6px 8px;
      border-radius: 4px;
      overflow-x: auto;
      white-space: pre-wrap;
      word-break: break-word;
    }

    .warnings-block {
      background: #fff8e1;
      border-left: 3px solid #e67e22;
      padding: 12px;
      border-radius: 0 4px 4px 0;
    }

    .warn-label {
      color: #c0392b;
    }

    .warn-list {
      margin: 4px 0 0;
      padding-left: 20px;
      font-size: 0.88rem;
      line-height: 1.6;
    }

    /* Decision log */
    .decision-log {
      border: 1px solid rgba(0,0,0,0.08);
      border-radius: 8px;
      overflow: hidden;
    }

    .decision-entry {
      padding: 12px 16px;
      border-bottom: 1px solid rgba(0,0,0,0.06);
      &:last-child { border-bottom: none; }
    }

    .decision-header {
      display: flex;
      align-items: center;
      gap: 8px;
      flex-wrap: wrap;
      margin-bottom: 4px;
    }

    .stage-tag {
      font-size: 0.7rem;
      font-weight: 600;
      text-transform: uppercase;
      padding: 2px 8px;
      border-radius: 4px;
      background: rgba(0,0,0,0.06);
    }

    .decision-action {
      font-size: 0.9rem;
    }

    .decision-ts {
      font-size: 0.75rem;
      opacity: 0.5;
      margin-left: auto;
    }

    .decision-reasoning {
      margin: 4px 0 0;
      font-size: 0.85rem;
      opacity: 0.8;
      line-height: 1.4;
    }
  `,
})
export class ExplainabilityPageComponent {
  private readonly pipeline = inject(PipelineService);

  readonly hasData = computed(() => !!this.pipeline.results()?.results?.length);

  readonly traces = computed<TraceWithAction[]>(() => {
    const results = this.pipeline.results()?.results ?? [];
    return results
      .filter((r: ResultEntry) => r.explainability_trace)
      .map((r: ResultEntry) => ({
        action: r.action,
        timestamp: r.timestamp,
        trace: r.explainability_trace!,
      }));
  });

  readonly decisionLog = computed<DecisionLogEntry[]>(() => {
    const results = this.pipeline.results()?.results ?? [];
    // Collect decision_log from any entry that has one (orchestrator adds it)
    const logs: DecisionLogEntry[] = [];
    for (const r of results) {
      if (Array.isArray(r.decision_log)) {
        logs.push(...r.decision_log);
      }
    }
    return logs;
  });

  confidenceClass(value: number): string {
    const pct = value > 1 ? value : value * 100;
    if (pct >= 70) return 'high';
    if (pct >= 40) return 'mid';
    return 'low';
  }

  hasAttributions(trace: ExplainabilityTrace): boolean {
    return !!trace.feature_attributions && Object.keys(trace.feature_attributions).length > 0;
  }

  formatTs(ts: string | undefined): string {
    if (!ts) return '';
    return ts.slice(0, 19).replace('T', ' ');
  }
}
