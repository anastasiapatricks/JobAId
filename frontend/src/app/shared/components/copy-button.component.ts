import { Component, Input } from '@angular/core';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatTooltipModule } from '@angular/material/tooltip';

@Component({
  selector: 'jobaid-copy-button',
  standalone: true,
  imports: [MatButtonModule, MatIconModule, MatTooltipModule],
  template: `
    <button
      mat-icon-button
      [matTooltip]="copied ? 'Copied!' : 'Copy to clipboard'"
      aria-label="Copy to clipboard"
      (click)="copy()"
    >
      <mat-icon>{{ copied ? 'check' : 'content_copy' }}</mat-icon>
    </button>
  `,
  styles: `
    button {
      opacity: 0.7;
      transition: opacity 0.2s;
    }
    button:hover {
      opacity: 1;
    }
  `,
})
export class CopyButtonComponent {
  @Input({ required: true }) text = '';
  copied = false;

  copy(): void {
    navigator.clipboard.writeText(this.text).then(() => {
      this.copied = true;
      setTimeout(() => (this.copied = false), 2000);
    });
  }
}
