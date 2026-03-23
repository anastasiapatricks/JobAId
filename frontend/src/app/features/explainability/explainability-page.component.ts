import { Component, inject, computed } from '@angular/core';
import { DecimalPipe, KeyValuePipe, JsonPipe } from '@angular/common';
import { MatIconModule } from '@angular/material/icon';
import { MatChipsModule } from '@angular/material/chips';
import { MatButtonModule } from '@angular/material/button';
import { MatTooltipModule } from '@angular/material/tooltip';
import { ReplacePipe } from '../../shared/pipes/replace.pipe';
import { PipelineService } from '../../core/services/pipeline.service';
import { XaiDrawerService } from '../../core/services/xai-drawer.service';
import { ExplainabilityTrace, DecisionLogEntry, ResultEntry } from '../../core/models/results.model';

interface TraceWithAction {
  action: string;
  timestamp: string;
  trace: ExplainabilityTrace;
}

const AGENT_META: Record<string, { icon: string; color: string; label: string }> = {
  resume_parser:       { icon: 'description',   color: '#0097A7', label: 'Resume Parser'       },
  orchestrator:        { icon: 'account_tree',   color: '#7B1FA2', label: 'Orchestrator'        },
  job_discovery:       { icon: 'work_outline',   color: '#1565C0', label: 'Job Discovery'       },
  market_intelligence: { icon: 'trending_up',    color: '#2E7D32', label: 'Market Intelligence' },
  pitch_generator:     { icon: 'edit_note',      color: '#E65100', label: 'Pitch Generator'     },
  summarizer:          { icon: 'summarize',      color: '#4527A0', label: 'Summarizer'          },
};

const DEFAULT_META = { icon: 'smart_toy', color: '#546E7A', label: '' };

@Component({
  selector: 'jobaid-explainability-panel',
  standalone: true,
  imports: [
    DecimalPipe,
    KeyValuePipe,
    JsonPipe,
    MatIconModule,
    MatChipsModule,
    MatButtonModule,
    MatTooltipModule,
    ReplacePipe,
  ],
  template: `
    <!-- ── Header ── -->
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
          <mat-icon>psychology</mat-icon>
          <p>Run the pipeline first — agent traces will appear here.</p>
        </div>
      } @else {

        <!-- ── Summary bar ── -->
        <div class="summary-bar">
          <div class="summary-stat">
            <span class="stat-num">{{ traces().length }}</span>
            <span class="stat-lbl">agents ran</span>
          </div>
          <div class="summary-divider"></div>
          <div class="summary-stat">
            <span class="stat-num" [class]="avgConfidenceClass()">{{ avgConfidence() | number:'1.0-0' }}%</span>
            <span class="stat-lbl">avg confidence</span>
          </div>
          <div class="summary-divider"></div>
          <div class="summary-stat">
            <span class="stat-num warn" [class.has-warn]="totalWarnings() > 0">{{ totalWarnings() }}</span>
            <span class="stat-lbl">warnings</span>
          </div>
        </div>

        <!-- ── Agent trace cards ── -->
        @for (item of traces(); track item.action + item.timestamp) {
          <div class="trace-card" [style.--agent-color]="agentMeta(item.trace.agent_name ?? '').color">

            <!-- Card header -->
            <div class="card-header">
              <div class="agent-icon-wrap">
                <mat-icon>{{ agentMeta(item.trace.agent_name ?? '').icon }}</mat-icon>
              </div>
              <div class="agent-info">
                <span class="agent-name">{{ agentMeta(item.trace.agent_name ?? '').label || item.trace.agent_name }}</span>
                <span class="agent-ts">{{ formatTs(item.trace.timestamp) }}</span>
              </div>
              <div class="confidence-ring" [class]="confidenceClass(item.trace.confidence ?? 0)">
                <span class="ring-num">{{ ((item.trace.confidence ?? 0) * 100) | number:'1.0-0' }}</span>
                <span class="ring-pct">%</span>
              </div>
            </div>

            <!-- Reasoning -->
            <p class="card-reasoning">{{ item.trace.reasoning }}</p>

            <!-- Grounding bar -->
            <div class="grounding-row">
              <span class="grounding-lbl">Grounding</span>
              <div class="grounding-track">
                <div class="grounding-fill"
                     [style.width.%]="(item.trace.grounding_score ?? 0) * 100"
                     [class]="confidenceClass(item.trace.grounding_score ?? 0)">
                </div>
              </div>
              <span class="grounding-val">{{ (item.trace.grounding_score ?? 0) | number:'1.2-2' }}</span>
            </div>

            <!-- Feature attributions (rendered intelligently per agent) -->
            @if (hasAttributions(item.trace)) {
              <div class="attr-section">
                <div class="attr-heading">
                  <mat-icon>bar_chart</mat-icon> Key Factors
                </div>
                {{ '' }}
                <!-- skill_gaps_with_explanations (market_intelligence) -->
                @if (getSkillGapAttrs(item.trace); as gaps) {
                  @if (gaps.length) {
                    <div class="skill-gap-list">
                      @for (g of gaps; track g.skill) {
                        <div class="skill-gap-row">
                          <mat-icon class="gap-icon">school</mat-icon>
                          <div class="gap-text">
                            <strong>{{ g.skill }}</strong>
                            @if (g.explanation) {
                              <span class="gap-expl">{{ g.explanation }}</span>
                            }
                          </div>
                        </div>
                      }
                    </div>
                  }
                }

                <!-- SHAP skill attributions (job_discovery) -->
                @if (getShapAttrs(item.trace); as shap) {
                  @if (shap.length) {
                    <div class="shap-list">
                      @for (entry of shap; track entry.skill) {
                        <div class="shap-row">
                          <span class="shap-skill">{{ entry.skill }}</span>
                          <div class="shap-bar-wrap">
                            <div class="shap-bar" [style.width.%]="entry.pct"
                                 [class]="entry.value > 0 ? 'positive' : 'zero'"></div>
                          </div>
                          <span class="shap-val" [class]="entry.value > 0 ? 'pos' : 'zero'">
                            {{ entry.value | number:'1.3-3' }}
                          </span>
                        </div>
                      }
                    </div>
                  }
                }

                <!-- match_analysis (pitch_generator) -->
                @if (getMatchAnalysis(item.trace); as ma) {
                  @if (ma) {
                    <div class="match-analysis">
                      @for (kv of ma | keyvalue; track kv.key) {
                        <div class="ma-row">
                          <span class="ma-key">{{ kv.key | replace }}</span>
                          <span class="ma-val">{{ kv.value }}</span>
                        </div>
                      }
                    </div>
                  }
                }

                <!-- feature attributions for resume_parser / orchestrator -->
                @if (getGenericAttrs(item.trace); as attrs) {
                  @if (attrs.length) {
                    <div class="generic-attrs">
                      @for (a of attrs; track a.key) {
                        <div class="generic-row">
                          <span class="generic-key">{{ a.key | replace }}</span>
                          <span class="generic-val">{{ a.value }}</span>
                        </div>
                      }
                    </div>
                  }
                }
              </div>
            }

            <!-- Sources -->
            @if (item.trace.sources_consulted?.length) {
              <div class="sources-row">
                <mat-icon class="sources-icon">source</mat-icon>
                @for (src of item.trace.sources_consulted; track src) {
                  <span class="source-chip">{{ src }}</span>
                }
              </div>
            }

            <!-- Warnings -->
            @if (item.trace.warnings?.length) {
              <div class="warnings-strip">
                <mat-icon>warning</mat-icon>
                <div class="warn-msgs">
                  @for (w of item.trace.warnings; track w) {
                    <span>{{ w }}</span>
                  }
                </div>
              </div>
            }

          </div>
        }

        <!-- ── Decision Log timeline ── -->
        @if (decisionLog().length) {
          <div class="section-divider">
            <mat-icon>history</mat-icon>
            Orchestrator Decisions
          </div>

          <div class="timeline">
            @for (entry of decisionLog(); track $index; let last = $last) {
              <div class="timeline-item" [class.last]="last">
                <div class="timeline-dot" [class]="actionClass(entry.action)"></div>
                <div class="timeline-content">
                  <div class="timeline-header">
                    <span class="tl-stage">{{ entry.stage }}</span>
                    <span class="tl-action" [class]="actionClass(entry.action)">{{ entry.action }}</span>
                    @if (entry.timestamp) {
                      <span class="tl-ts">{{ formatTs(entry.timestamp) }}</span>
                    }
                  </div>
                  @if (entry.reasoning) {
                    <p class="tl-reasoning">{{ entry.reasoning }}</p>
                  }
                </div>
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
      background: #f8f9fb;
    }

    /* ── Header ── */
    .drawer-header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 14px 12px 14px 20px;
      background: white;
      border-bottom: 1px solid #e0e0e0;
      flex-shrink: 0;
    }

    .drawer-title {
      display: flex;
      align-items: center;
      gap: 8px;
      font-weight: 700;
      font-size: 1rem;
      color: #1a1a2e;
      mat-icon { color: #5c6bc0; font-size: 20px; width: 20px; height: 20px; }
    }

    /* ── Scrollable body ── */
    .drawer-body {
      flex: 1;
      overflow-y: auto;
      padding: 16px;
      display: flex;
      flex-direction: column;
      gap: 12px;
    }

    /* ── Empty state ── */
    .empty-state {
      display: flex;
      flex-direction: column;
      align-items: center;
      gap: 12px;
      padding: 48px 16px;
      color: #9e9e9e;
      text-align: center;
      mat-icon { font-size: 48px; width: 48px; height: 48px; opacity: 0.3; }
      p { margin: 0; font-size: 0.9rem; }
    }

    /* ── Summary bar ── */
    .summary-bar {
      display: flex;
      align-items: center;
      background: white;
      border-radius: 10px;
      padding: 12px 16px;
      box-shadow: 0 1px 3px rgba(0,0,0,0.08);
      gap: 0;
      flex-shrink: 0;
    }

    .summary-stat {
      flex: 1;
      display: flex;
      flex-direction: column;
      align-items: center;
      gap: 2px;
    }

    .stat-num {
      font-size: 1.4rem;
      font-weight: 700;
      color: #1a1a2e;
      line-height: 1;
      &.high { color: #2e7d32; }
      &.mid  { color: #e65100; }
      &.low  { color: #c62828; }
    }

    .stat-lbl {
      font-size: 0.68rem;
      text-transform: uppercase;
      letter-spacing: 0.5px;
      color: #9e9e9e;
      font-weight: 500;
    }

    .stat-num.warn { color: #9e9e9e; }
    .stat-num.warn.has-warn { color: #e65100; }

    .summary-divider {
      width: 1px;
      height: 32px;
      background: #e0e0e0;
      flex-shrink: 0;
    }

    /* ── Trace card ── */
    .trace-card {
      background: white;
      border-radius: 10px;
      border-left: 4px solid var(--agent-color, #546E7A);
      box-shadow: 0 1px 3px rgba(0,0,0,0.08);
      padding: 14px 16px;
      display: flex;
      flex-direction: column;
      gap: 10px;
    }

    .card-header {
      display: flex;
      align-items: center;
      gap: 10px;
    }

    .agent-icon-wrap {
      width: 36px;
      height: 36px;
      border-radius: 8px;
      background: color-mix(in srgb, var(--agent-color, #546E7A) 12%, white);
      display: flex;
      align-items: center;
      justify-content: center;
      flex-shrink: 0;
      mat-icon {
        font-size: 20px;
        width: 20px;
        height: 20px;
        color: var(--agent-color, #546E7A);
      }
    }

    .agent-info {
      flex: 1;
      display: flex;
      flex-direction: column;
      gap: 1px;
    }

    .agent-name {
      font-weight: 600;
      font-size: 0.88rem;
      color: #1a1a2e;
    }

    .agent-ts {
      font-size: 0.72rem;
      color: #bdbdbd;
    }

    .confidence-ring {
      display: flex;
      align-items: baseline;
      gap: 1px;
      padding: 4px 10px;
      border-radius: 20px;
      flex-shrink: 0;
      font-weight: 700;

      &.high { background: #e8f5e9; color: #2e7d32; }
      &.mid  { background: #fff8e1; color: #e65100; }
      &.low  { background: #ffebee; color: #c62828; }
    }

    .ring-num { font-size: 1.1rem; }
    .ring-pct { font-size: 0.7rem; opacity: 0.7; }

    /* Reasoning */
    .card-reasoning {
      margin: 0;
      font-size: 0.875rem;
      line-height: 1.55;
      color: #37474f;
    }

    /* Grounding bar */
    .grounding-row {
      display: flex;
      align-items: center;
      gap: 8px;
    }

    .grounding-lbl {
      font-size: 0.7rem;
      text-transform: uppercase;
      letter-spacing: 0.4px;
      color: #9e9e9e;
      font-weight: 600;
      flex-shrink: 0;
      width: 62px;
    }

    .grounding-track {
      flex: 1;
      height: 5px;
      border-radius: 3px;
      background: #eeeeee;
      overflow: hidden;
    }

    .grounding-fill {
      height: 100%;
      border-radius: 3px;
      transition: width 0.4s ease;
      &.high { background: #43a047; }
      &.mid  { background: #ffa726; }
      &.low  { background: #ef5350; }
    }

    .grounding-val {
      font-size: 0.72rem;
      font-weight: 600;
      color: #757575;
      flex-shrink: 0;
      width: 30px;
      text-align: right;
    }

    /* Attributions */
    .attr-section {
      background: #f5f7fa;
      border-radius: 7px;
      padding: 10px 12px;
      display: flex;
      flex-direction: column;
      gap: 8px;
    }

    .attr-heading {
      display: flex;
      align-items: center;
      gap: 4px;
      font-size: 0.7rem;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0.5px;
      color: #757575;
      mat-icon { font-size: 13px; width: 13px; height: 13px; }
    }

    /* Skill gap list */
    .skill-gap-list { display: flex; flex-direction: column; gap: 6px; }

    .skill-gap-row {
      display: flex;
      align-items: flex-start;
      gap: 7px;
    }

    .gap-icon {
      font-size: 14px; width: 14px; height: 14px;
      color: #5c6bc0; margin-top: 2px; flex-shrink: 0;
    }

    .gap-text {
      display: flex;
      flex-direction: column;
      gap: 1px;
      strong { font-size: 0.82rem; color: #1a1a2e; }
    }

    .gap-expl {
      font-size: 0.76rem;
      color: #757575;
      line-height: 1.4;
    }

    /* SHAP bars */
    .shap-list { display: flex; flex-direction: column; gap: 5px; }

    .shap-row {
      display: flex;
      align-items: center;
      gap: 8px;
    }

    .shap-skill {
      font-size: 0.76rem;
      width: 110px;
      flex-shrink: 0;
      color: #37474f;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }

    .shap-bar-wrap {
      flex: 1;
      height: 6px;
      background: #eeeeee;
      border-radius: 3px;
      overflow: hidden;
    }

    .shap-bar {
      height: 100%;
      border-radius: 3px;
      min-width: 3px;
      &.positive { background: #5c6bc0; }
      &.zero     { background: #bdbdbd; }
    }

    .shap-val {
      font-size: 0.72rem;
      font-weight: 600;
      width: 40px;
      text-align: right;
      flex-shrink: 0;
      &.pos  { color: #5c6bc0; }
      &.zero { color: #bdbdbd; }
    }

    /* Match analysis / generic */
    .match-analysis, .generic-attrs {
      display: flex;
      flex-direction: column;
      gap: 4px;
    }

    .ma-row, .generic-row {
      display: flex;
      gap: 8px;
      font-size: 0.8rem;
      align-items: baseline;
    }

    .ma-key, .generic-key {
      color: #9e9e9e;
      font-weight: 500;
      flex-shrink: 0;
      width: 120px;
      font-size: 0.75rem;
    }

    .ma-val, .generic-val {
      color: #37474f;
      flex: 1;
    }

    /* Sources */
    .sources-row {
      display: flex;
      align-items: center;
      gap: 6px;
      flex-wrap: wrap;
      mat-icon { font-size: 13px; width: 13px; height: 13px; color: #9e9e9e; flex-shrink: 0; }
    }

    .source-chip {
      font-size: 0.7rem;
      padding: 2px 8px;
      border-radius: 10px;
      background: #ede7f6;
      color: #4527a0;
      font-weight: 500;
    }

    /* Warnings */
    .warnings-strip {
      display: flex;
      align-items: flex-start;
      gap: 7px;
      background: #fff8e1;
      border-radius: 6px;
      padding: 8px 10px;
      mat-icon { font-size: 15px; width: 15px; height: 15px; color: #e65100; flex-shrink: 0; margin-top: 1px; }
    }

    .warn-msgs {
      display: flex;
      flex-direction: column;
      gap: 2px;
      span { font-size: 0.78rem; color: #bf360c; line-height: 1.4; }
    }

    /* ── Section divider ── */
    .section-divider {
      display: flex;
      align-items: center;
      gap: 6px;
      font-size: 0.72rem;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0.6px;
      color: #9e9e9e;
      margin-top: 4px;
      mat-icon { font-size: 14px; width: 14px; height: 14px; }

      &::before, &::after {
        content: '';
        flex: 1;
        height: 1px;
        background: #e0e0e0;
      }
    }

    /* ── Timeline ── */
    .timeline {
      display: flex;
      flex-direction: column;
      padding-left: 8px;
    }

    .timeline-item {
      display: flex;
      gap: 12px;
      position: relative;
      padding-bottom: 12px;

      &::before {
        content: '';
        position: absolute;
        left: 7px;
        top: 16px;
        bottom: 0;
        width: 1px;
        background: #e0e0e0;
      }

      &.last::before { display: none; }
    }

    .timeline-dot {
      width: 15px;
      height: 15px;
      border-radius: 50%;
      flex-shrink: 0;
      margin-top: 3px;
      border: 2px solid currentColor;

      &.advance  { color: #43a047; background: #e8f5e9; }
      &.retry    { color: #ffa726; background: #fff8e1; }
      &.skip     { color: #ef5350; background: #ffebee; }
      &.force_complete { color: #9e9e9e; background: #f5f5f5; }
      &.default  { color: #bdbdbd; background: #f5f5f5; }
    }

    .timeline-content {
      flex: 1;
      min-width: 0;
    }

    .timeline-header {
      display: flex;
      align-items: center;
      gap: 6px;
      flex-wrap: wrap;
      margin-bottom: 2px;
    }

    .tl-stage {
      font-size: 0.7rem;
      padding: 1px 6px;
      border-radius: 4px;
      background: #f5f5f5;
      color: #757575;
      font-weight: 500;
      text-transform: uppercase;
    }

    .tl-action {
      font-size: 0.78rem;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0.3px;

      &.advance  { color: #2e7d32; }
      &.retry    { color: #e65100; }
      &.skip     { color: #c62828; }
      &.force_complete { color: #757575; }
      &.default  { color: #546e7a; }
    }

    .tl-ts {
      font-size: 0.68rem;
      color: #bdbdbd;
      margin-left: auto;
    }

    .tl-reasoning {
      margin: 0;
      font-size: 0.8rem;
      color: #546e7a;
      line-height: 1.4;
    }
  `,
})
export class ExplainabilityPageComponent {
  private readonly pipeline = inject(PipelineService);
  protected readonly xaiDrawer = inject(XaiDrawerService);

  readonly hasData = computed(() => !!this.pipeline.results()?.results?.length);

  readonly traces = computed<TraceWithAction[]>(() => {
    const results = this.pipeline.results()?.results ?? [];
    const out: TraceWithAction[] = [];
    for (const r of results) {
      if (!r.explainability_trace) continue;
      const raw = r.explainability_trace;
      const traceList: ExplainabilityTrace[] = Array.isArray(raw) ? raw : [raw as ExplainabilityTrace];
      for (const trace of traceList) {
        out.push({ action: r.action, timestamp: r.timestamp, trace });
      }
    }
    return out;
  });

  readonly decisionLog = computed<DecisionLogEntry[]>(() => {
    const results = this.pipeline.results()?.results ?? [];
    const logs: DecisionLogEntry[] = [];
    for (const r of results) {
      if (Array.isArray(r.decision_log)) logs.push(...r.decision_log);
    }
    return logs;
  });

  readonly avgConfidence = computed(() => {
    const t = this.traces();
    if (!t.length) return 0;
    return (t.reduce((s, i) => s + (i.trace.confidence ?? 0), 0) / t.length) * 100;
  });

  readonly avgConfidenceClass = computed(() => this.confidenceClass(this.avgConfidence() / 100));

  readonly totalWarnings = computed(() =>
    this.traces().reduce((s, i) => s + (i.trace.warnings?.length ?? 0), 0)
  );

  agentMeta(name: string) {
    return AGENT_META[name] ?? { ...DEFAULT_META, label: name };
  }

  confidenceClass(value: number): string {
    const pct = value > 1 ? value : value * 100;
    if (pct >= 70) return 'high';
    if (pct >= 40) return 'mid';
    return 'low';
  }

  hasAttributions(trace: ExplainabilityTrace): boolean {
    return !!trace.feature_attributions && Object.keys(trace.feature_attributions).length > 0;
  }

  /** skill_gaps_with_explanations from market_intelligence */
  getSkillGapAttrs(trace: ExplainabilityTrace): { skill: string; explanation: string }[] | null {
    const v = trace.feature_attributions?.['skill_gaps_with_explanations'];
    if (!Array.isArray(v) || !v.length) return null;
    return v as { skill: string; explanation: string }[];
  }

  /** top_job_shap from job_discovery — normalise to bar widths */
  getShapAttrs(trace: ExplainabilityTrace): { skill: string; value: number; pct: number }[] | null {
    const raw = trace.feature_attributions?.['top_job_shap'] as Record<string, unknown> | undefined;
    if (!raw || typeof raw !== 'object' || Array.isArray(raw)) return null;
    const entries = Object.entries(raw)
      .filter(([k]) => k !== '_meta')
      .map(([skill, val]) => ({ skill, value: typeof val === 'number' ? val : 0 }))
      .sort((a, b) => b.value - a.value)
      .slice(0, 8);
    if (!entries.length) return null;
    const max = Math.max(...entries.map(e => Math.abs(e.value)), 0.001);
    return entries.map(e => ({ ...e, pct: Math.round((Math.abs(e.value) / max) * 100) }));
  }

  /** match_analysis from pitch_generator */
  getMatchAnalysis(trace: ExplainabilityTrace): Record<string, unknown> | null {
    const v = trace.feature_attributions?.['match_analysis'];
    if (!v || typeof v !== 'object' || Array.isArray(v)) return null;
    return v as Record<string, unknown>;
  }

  /**
   * Fallback for resume_parser / orchestrator — simple key-value pairs,
   * skip anything already handled by the specific renderers above.
   */
  getGenericAttrs(trace: ExplainabilityTrace): { key: string; value: string }[] | null {
    const fa = trace.feature_attributions;
    if (!fa) return null;
    const skip = new Set(['skill_gaps_with_explanations', 'top_job_shap', 'match_analysis']);
    const entries = Object.entries(fa)
      .filter(([k]) => !skip.has(k))
      .map(([key, val]) => ({
        key,
        value: typeof val === 'object' ? JSON.stringify(val, null, 1) : String(val),
      }));
    return entries.length ? entries : null;
  }

  actionClass(action: string): string {
    if (action === 'advance') return 'advance';
    if (action === 'retry') return 'retry';
    if (action === 'skip') return 'skip';
    if (action === 'force_complete') return 'force_complete';
    return 'default';
  }

  formatTs(ts: string | undefined): string {
    if (!ts) return '';
    return ts.slice(0, 19).replace('T', ' ');
  }
}
