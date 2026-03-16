import { Component, Output, EventEmitter, ViewChild, ElementRef } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatTooltipModule } from '@angular/material/tooltip';

@Component({
  selector: 'jobaid-chat-input',
  standalone: true,
  imports: [FormsModule, MatButtonModule, MatIconModule, MatFormFieldModule, MatInputModule, MatTooltipModule],
  template: `
    <div class="chat-input-container">
      <button
        mat-icon-button
        matTooltip="Attach resume file"
        aria-label="Attach file"
        (click)="fileInput.click()"
        class="attach-btn"
      >
        <mat-icon>attach_file</mat-icon>
      </button>
      <input
        #fileInput
        type="file"
        hidden
        accept=".pdf,.txt,.doc,.docx"
        (change)="onFileSelected($event)"
      />
      <mat-form-field class="message-field" appearance="outline" subscriptSizing="dynamic">
        <input
          matInput
          #messageInput
          [(ngModel)]="message"
          placeholder="Type a message..."
          (keydown.enter)="send()"
          autocomplete="off"
        />
      </mat-form-field>
      <button
        mat-icon-button
        color="primary"
        aria-label="Send message"
        (click)="send()"
        [disabled]="!message.trim()"
        class="send-btn"
      >
        <mat-icon>send</mat-icon>
      </button>
    </div>
  `,
  styles: `
    .chat-input-container {
      display: flex;
      align-items: center;
      gap: 10px;
      padding: 14px 16px;
      background: rgba(255, 255, 255, 0.92);
      backdrop-filter: blur(10px);
      border-top: 1px solid var(--app-border);
    }

    .message-field {
      flex: 1;
    }

    .attach-btn,
    .send-btn {
      flex-shrink: 0;
      border-radius: 999px;
    }

    .attach-btn {
      opacity: 0.75;
      color: var(--app-text-muted);
    }

    .attach-btn:hover {
      opacity: 1;
      background: var(--app-accent-soft);
    }

    .send-btn {
      background: var(--app-brand-soft);
      color: var(--app-brand-dark);
    }

    .send-btn:hover {
      background: #bfdbfe;
    }
  `,
})
export class ChatInputComponent {
  @Output() messageSent = new EventEmitter<string>();
  @Output() fileSelected = new EventEmitter<File>();
  @ViewChild('messageInput') messageInput!: ElementRef<HTMLInputElement>;

  message = '';

  send(): void {
    const text = this.message.trim();
    if (!text) return;
    this.messageSent.emit(text);
    this.message = '';
  }

  onFileSelected(event: Event): void {
    const input = event.target as HTMLInputElement;
    const file = input.files?.[0];
    if (file) {
      this.fileSelected.emit(file);
      input.value = '';
    }
  }

  focus(): void {
    this.messageInput?.nativeElement?.focus();
  }
}
