import { Component, Input } from '@angular/core';
import { ChatMessage } from '../../../core/services/chat.service';
import { MessageBubbleComponent } from './message-bubble.component';
import { TypingIndicatorComponent } from './typing-indicator.component';
import { AutoScrollDirective } from '../../../shared/directives/auto-scroll.directive';

@Component({
  selector: 'jobaid-message-list',
  standalone: true,
  imports: [MessageBubbleComponent, TypingIndicatorComponent, AutoScrollDirective],
  template: `
    <div class="message-list" role="log" aria-label="Chat messages" [jobaidAutoScroll]="true" scrollMode="smart">
      @for (msg of messages; track msg.id) {
        <jobaid-message-bubble [message]="msg"></jobaid-message-bubble>
      }
      @if (isTyping) {
        <jobaid-typing-indicator [message]="typingMessage"></jobaid-typing-indicator>
      }
    </div>
  `,
  styles: `
    :host {
      display: flex;
      flex: 1;
      overflow: hidden;
      min-height: 0;
    }
    .message-list {
      flex: 1;
      overflow-y: auto;
      padding: 24px 16px;
      display: flex;
      flex-direction: column;
    }
  `,
})
export class MessageListComponent {
  @Input({ required: true }) messages: ChatMessage[] = [];
  @Input() isTyping = false;
  @Input() typingMessage = 'Analyzing...';
}
