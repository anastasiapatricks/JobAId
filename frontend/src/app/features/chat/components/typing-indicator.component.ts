import { Component, Input } from '@angular/core';

@Component({
  selector: 'jobaid-typing-indicator',
  standalone: true,
  template: `
    <div class="typing-indicator">
      <span class="dot"></span>
      <span class="dot"></span>
      <span class="dot"></span>
      <span class="label">{{ message }}</span>
    </div>
  `,
  styles: `
    .typing-indicator {
      display: flex;
      align-items: center;
      gap: 4px;
      padding: 12px 16px;
      background: var(--mat-sys-surface-container);
      border-radius: 18px 18px 18px 4px;
      width: fit-content;
    }
    .dot {
      width: 8px;
      height: 8px;
      border-radius: 50%;
      background: var(--mat-sys-primary);
      opacity: 0.4;
      animation: bounce 1.4s infinite ease-in-out both;
    }
    .dot:nth-child(1) { animation-delay: -0.32s; }
    .dot:nth-child(2) { animation-delay: -0.16s; }
    .dot:nth-child(3) { animation-delay: 0s; }
    .label {
      margin-left: 8px;
      font-size: 0.85rem;
      opacity: 0.6;
    }
    @keyframes bounce {
      0%, 80%, 100% { transform: scale(0); }
      40% { transform: scale(1); }
    }
  `,
})
export class TypingIndicatorComponent {
  @Input() message = 'Analyzing...';
}
