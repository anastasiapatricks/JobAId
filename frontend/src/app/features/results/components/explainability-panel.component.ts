import { Component, Input } from '@angular/core';
import { DecimalPipe } from '@angular/common';
import { MatIconModule } from '@angular/material/icon';
import { MatChipsModule } from '@angular/material/chips';
import { ExplainabilityTrace } from '../../../core/models/results.model';

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
  imports: [DecimalPipe, MatIconModule, MatChipsModule],
  template: `
    @if (!trace) {
      <div class="empty-state">
        <mat-icon>psychology</mat-icon>
        <p>No explainability data for this step.</p>
      </div>
    } @else {
      @for (t of traceArray(); track $index) {
        <div class="trace-card" [style.--agent-color]="agentMeta(t.agent_name).color">
          <div class="card-header">
            <div class="agent-icon-wrap">
              <mat-icon>{{ agentMeta(t.agent_name).icon }}</mat-icon>
            </div>
            <div class="agent-info">
              <span class="agent-name">{{ agentMeta(t.agent_name).label || t.agent_name }}</span>
              @if (t.timestamp) {
                <span class="agent-ts">{{ formatTs(t.timestamp) }}</span>
              }
            </div>
            @if (t.confidence != null) {
              <div class="confidence-badge" [class]="confidenceClass(t.confidence)">
                {{ (t.confidence * 100) | number:'1.0-0' }}%
              </div>
            }
          </div>

          @if (t.reasoning) {
            <p class="card-reasoning">{{ t.reasoning }}</p>
          }

          @if (t.grounding_score != null) {
            <div class="grounding-row">
              <span class="grounding-lbl">Grounding</span>
              <div class="grounding-track">
                <div class="grounding-fill"
                     [style.width.%]="t.grounding_score * 100"
                     [class]="confidenceClass(t.grounding_score)">
                </div>
              </div>
              <span class="grounding-val">{{ t.grounding_score | number:'1.2-2' }}</span>
            </div>
          }

          @if (t.sources_consulted?.length) {
            <div class="sources-row">
              <mat-icon class="sources-icon">source</mat-icon>
              @for (src of t.sources_consulted; track src) {
                <span class="source-chip">{{ src }}</span>
              }
            </div>
          }

          @if (t.warnings?.length) {
            <div class="warnings-strip">
              <mat-icon>warning</mat-icon>
              <div class="warn-msgs">
                @for (w of t.warnings; track w) { <span>{{ w }}</span> }
              </div>
            </div>
          }
        </div>
      }
    }
  `,
  styles: `
    :host { display: flex; flex-direction: column; gap: 12px; }

    .empty-state {
      display: flex; flex-direction: column; align-items: center; gap: 10px;
      padding: 32px 16px; color: #9e9e9e; text-align: center;
      mat-icon { font-size: 40px; width: 40px; height: 40px; opacity: 0.3; }
      p { margin: 0; font-size: 0.88rem; }
    }

    .trace-card {
      background: white; border-radius: 10px;
      border-left: 4px solid var(--agent-color, #546E7A);
      box-shadow: 0 1px 3px rgba(0,0,0,0.08);
      padding: 14px 16px; display: flex; flex-direction: column; gap: 10px;
    }

    .card-header { display: flex; align-items: center; gap: 10px; }

    .agent-icon-wrap {
      width: 34px; height: 34px; border-radius: 8px;
      background: color-mix(in srgb, var(--agent-color, #546E7A) 12%, white);
      display: flex; align-items: center; justify-content: center; flex-shrink: 0;
      mat-icon { font-size: 18px; width: 18px; height: 18px; color: var(--agent-color, #546E7A); }
    }

    .agent-info { flex: 1; display: flex; flex-direction: column; gap: 1px; }
    .agent-name { font-weight: 600; font-size: 0.86rem; color: #1a1a2e; }
    .agent-ts   { font-size: 0.7rem; color: #bdbdbd; }

    .confidence-badge {
      padding: 3px 10px; border-radius: 20px; font-weight: 700; font-size: 0.85rem;
      &.high { background: #e8f5e9; color: #2e7d32; }
      &.mid  { background: #fff8e1; color: #e65100; }
      &.low  { background: #ffebee; color: #c62828; }
    }

    .card-reasoning { margin: 0; font-size: 0.875rem; line-height: 1.55; color: #37474f; }

    .grounding-row { display: flex; align-items: center; gap: 8px; }
    .grounding-lbl {
      font-size: 0.7rem; text-transform: uppercase; letter-spacing: 0.4px;
      color: #9e9e9e; font-weight: 600; flex-shrink: 0; width: 62px;
    }
    .grounding-track { flex: 1; height: 5px; border-radius: 3px; background: #eeeeee; overflow: hidden; }
    .grounding-fill {
      height: 100%; border-radius: 3px; transition: width 0.4s ease;
      &.high { background: #43a047; }
      &.mid  { background: #ffa726; }
      &.low  { background: #ef5350; }
    }
    .grounding-val { font-size: 0.72rem; font-weight: 600; color: #757575; flex-shrink: 0; width: 30px; text-align: right; }

    .sources-row {
      display: flex; align-items: center; gap: 6px; flex-wrap: wrap;
      mat-icon { font-size: 13px; width: 13px; height: 13px; color: #9e9e9e; flex-shrink: 0; }
    }
    .source-chip { font-size: 0.7rem; padding: 2px 8px; border-radius: 10px; background: #ede7f6; color: #4527a0; font-weight: 500; }

    .warnings-strip {
      display: flex; align-items: flex-start; gap: 7px;
      background: #fff8e1; border-radius: 6px; padding: 8px 10px;
      mat-icon { font-size: 15px; width: 15px; height: 15px; color: #e65100; flex-shrink: 0; margin-top: 1px; }
    }
    .warn-msgs { display: flex; flex-direction: column; gap: 2px; span { font-size: 0.78rem; color: #bf360c; line-height: 1.4; } }
  `,
})
export class ExplainabilityPanelComponent {
  @Input() trace: ExplainabilityTrace | ExplainabilityTrace[] | null | undefined;

  traceArray(): ExplainabilityTrace[] {
    if (!this.trace) return [];
    return Array.isArray(this.trace) ? this.trace : [this.trace];
  }

  agentMeta(name: string | undefined) {
    return AGENT_META[name ?? ''] ?? { ...DEFAULT_META, label: name ?? 'Agent' };
  }

  confidenceClass(value: number): string {
    const pct = value > 1 ? value : value * 100;
    if (pct >= 70) return 'high';
    if (pct >= 40) return 'mid';
    return 'low';
  }

  formatTs(ts: string | undefined): string {
    if (!ts) return '';
    return ts.slice(0, 19).replace('T', ' ');
  }
}
