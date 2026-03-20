import { Component, inject, computed } from '@angular/core';
import { DecimalPipe, KeyValuePipe, JsonPipe } from '@angular/common';
import { MatIconModule } from '@angular/material/icon';
import { MatExpansionModule } from '@angular/material/expansion';
import { MatChipsModule } from '@angular/material/chips';
import { MatDividerModule } from '@angular/material/divider';
import { MatButtonModule } from '@angular/material/button';
import { PipelineService } from '../../core/services/pipeline.service';
import { XaiDrawerService } from '../../core/services/xai-drawer.service';
import { ExplainabilityTrace, DecisionLogEntry, ResultEntry } from '../../core/models/results.model';

interface TraceWithAction {
  action: string;
  timestamp: string;
  trace: ExplainabilityTrace;
}

@Component({
  selector: 'jobaid-explainability-panel',
  standalone: true,
  imports: [
    DecimalPipe,
    KeyValuePipe,
    JsonPipe,
    MatIconModule,
    MatExpansionModule,
    MatChipsModule,
    MatDividerModule,
    MatButtonModule,
  ],
  template: `
    <div class="drawer-header">
      <div class="drawer-title">
        <mat-icon>psychology</mat-icon>
        <span>Explainability Log</span>
      </div>
      <button mat-icon-button (click)="xaiDrawer.close()" aria-label="Close">
        <mat-icon>close</mat-icon>
      </button>
    </div>

    <div class="drawer-body">
      @if (!hasData()) {
        <div class="empty-state">
          <mat-icon>info_outline</mat-icon>
          <p>Run the pipeline first — agent traces will appear here.</p>
        </div>
      } @else {

        <!-- Agent XAI Traces -->
        @if (traces().length) {
          <h3 class="section-heading">
            <mat-icon>analytics</mat-icon>
            Agent Traces ({{ traces().length }})
          </h3>

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
                      {{ (item.trace.confidence * 100) | number:'1.0-0' }}%
                    </span>
                    @if (item.trace.warnings?.length) {
                      <mat-icon class="warn-icon">warning</mat-icon>
                    }
                  </mat-panel-description>
                </mat-expansion-panel-header>

                <div class="trace-body">
                  <div class="meta-row">
                    <span class="meta-label">Prompt</span>
                    <code class="meta-value">{{ item.trace.prompt_version }}</code>
                    <span class="meta-label">Time</span>
                    <span class="meta-value">{{ formatTs(item.trace.timestamp) }}</span>
                  </div>

                  <mat-divider></mat-divider>

                  <!-- Reasoning -->
                  <div class="trace-block">
                    <div class="block-label"><mat-icon>chat_bubble_outline</mat-icon> Reasoning</div>
                    <p class="block-text">{{ item.trace.reasoning }}</p>
                  </div>

                  <!-- Grounding score -->
                  <div class="trace-block">
                    <div class="block-label"><mat-icon>verified</mat-icon> Grounding</div>
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
                      <div class="block-label"><mat-icon>bar_chart</mat-icon> Attributions</div>
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

                  <!-- Sources -->
                  @if (item.trace.sources_consulted?.length) {
                    <div class="trace-block">
                      <div class="block-label"><mat-icon>source</mat-icon> Sources</div>
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
                      <div class="block-label warn-label"><mat-icon>warning</mat-icon> Warnings</div>
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
        }

        <!-- Decision Log -->
        @if (decisionLog().length) {
          <h3 class="section-heading" style="margin-top: 24px;">
            <mat-icon>history</mat-icon>
            Decision Log ({{ decisionLog().length }})
          </h3>

          <div class="decision-log">
            @for (entry of decisionLog(); track $index) {
              <div class="decision-entry">
                <div class="decision-header">
                  <span class="stage-tag">{{ entry.stage }}</span>
                  <strong>{{ entry.action }}</strong>
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
        }

      }
    </div>
  `,
  styles: `
    :host {
      display: flex;
      flex-direction: column;
      height: 100%;
      overflow: hidden;
    }

    /* Header */
    .drawer-header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 12px 16px 12px 20px;
      border-bottom: 1px solid rgba(0,0,0,0.1);
      flex-shrink: 0;
      background: var(--mat-sys-surface-container-low);
    }

    .drawer-title {
      display: flex;
      align-items: center;
      gap: 8px;
      font-weight: 600;
      font-size: 1rem;
      mat-icon { color: var(--mat-sys-primary); }
    }

    /* Scrollable body */
    .drawer-body {
      flex: 1;
      overflow-y: auto;
      padding: 16px;
    }

    .empty-state {
      display: flex;
      flex-direction: column;
      align-items: center;
      gap: 12px;
      padding: 40px 16px;
      color: var(--mat-sys-on-surface-variant);
      text-align: center;
      mat-icon { font-size: 40px; width: 40px; height: 40px; opacity: 0.4; }
      p { margin: 0; font-size: 0.9rem; }
    }

    .section-heading {
      display: flex;
      align-items: center;
      gap: 6px;
      font-size: 0.85rem;
      font-weight: 600;
      text-transform: uppercase;
      letter-spacing: 0.5px;
      color: var(--mat-sys-on-surface-variant);
      margin: 0 0 12px;
      mat-icon { font-size: 16px; width: 16px; height: 16px; color: var(--mat-sys-primary); }
    }

    /* Trace panels */
    .trace-panel { margin-bottom: 6px; }

    .trace-title {
      display: flex;
      align-items: center;
      gap: 6px;
      font-size: 0.85rem;
    }

    .agent-tag {
      font-size: 0.7rem;
      font-weight: 700;
      text-transform: uppercase;
      padding: 1px 6px;
      border-radius: 4px;
      background: var(--mat-sys-primary-container);
      color: var(--mat-sys-on-primary-container);
    }

    .action-label { font-size: 0.85rem; font-weight: 500; }

    .trace-desc {
      display: flex;
      align-items: center;
      gap: 6px;
    }

    .confidence-badge {
      font-size: 0.72rem;
      font-weight: 700;
      padding: 1px 6px;
      border-radius: 10px;
      &.high { background: #d4edda; color: #155724; }
      &.mid  { background: #fff3cd; color: #856404; }
      &.low  { background: #f8d7da; color: #721c24; }
    }

    .warn-icon {
      font-size: 16px; width: 16px; height: 16px; color: #e67e22;
    }

    .trace-body { padding: 4px 0; }

    .meta-row {
      display: flex;
      align-items: center;
      gap: 6px;
      flex-wrap: wrap;
      font-size: 0.75rem;
      padding: 4px 0 10px;
    }

    .meta-label { color: var(--mat-sys-on-surface-variant); font-weight: 500; }
    .meta-value { font-family: monospace; font-size: 0.75rem; }

    .trace-block { margin: 12px 0; }

    .block-label {
      display: flex;
      align-items: center;
      gap: 4px;
      font-size: 0.72rem;
      font-weight: 600;
      text-transform: uppercase;
      letter-spacing: 0.4px;
      color: var(--mat-sys-on-surface-variant);
      margin-bottom: 6px;
      mat-icon { font-size: 14px; width: 14px; height: 14px; }
    }

    .block-text { margin: 0; font-size: 0.85rem; line-height: 1.5; }

    .score-bar-wrap {
      display: flex; align-items: center; gap: 10px;
    }

    .score-bar {
      flex: 1; height: 6px; border-radius: 3px;
      background: rgba(0,0,0,0.08); overflow: hidden;
    }

    .score-fill {
      height: 100%; border-radius: 3px;
      &.high { background: #28a745; }
      &.mid  { background: #ffc107; }
      &.low  { background: #dc3545; }
    }

    .score-label { font-size: 0.8rem; font-weight: 600; min-width: 32px; }

    .attr-grid { display: flex; flex-direction: column; gap: 6px; }

    .attr-entry { display: flex; flex-direction: column; gap: 2px; }

    .attr-key { font-size: 0.75rem; font-weight: 600; color: var(--mat-sys-on-surface-variant); }

    .attr-val {
      margin: 0; font-size: 0.72rem; font-family: monospace;
      background: rgba(0,0,0,0.04); padding: 4px 6px; border-radius: 4px;
      overflow-x: auto; white-space: pre-wrap; word-break: break-word;
    }

    .warnings-block {
      background: #fff8e1;
      border-left: 3px solid #e67e22;
      padding: 8px 10px;
      border-radius: 0 4px 4px 0;
    }

    .warn-label { color: #c0392b; }

    .warn-list {
      margin: 4px 0 0; padding-left: 18px;
      font-size: 0.82rem; line-height: 1.6;
    }

    /* Decision log */
    .decision-log {
      border: 1px solid rgba(0,0,0,0.08);
      border-radius: 8px; overflow: hidden;
    }

    .decision-entry {
      padding: 10px 14px;
      border-bottom: 1px solid rgba(0,0,0,0.06);
      &:last-child { border-bottom: none; }
    }

    .decision-header {
      display: flex; align-items: center; gap: 6px; flex-wrap: wrap;
    }

    .stage-tag {
      font-size: 0.68rem; font-weight: 600; text-transform: uppercase;
      padding: 1px 6px; border-radius: 4px; background: rgba(0,0,0,0.06);
    }

    .decision-ts { font-size: 0.72rem; opacity: 0.5; margin-left: auto; }

    .decision-reasoning {
      margin: 4px 0 0; font-size: 0.82rem; opacity: 0.8; line-height: 1.4;
    }
  `,
})
export class ExplainabilityPageComponent {
  private readonly pipeline = inject(PipelineService);
  protected readonly xaiDrawer = inject(XaiDrawerService);

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
