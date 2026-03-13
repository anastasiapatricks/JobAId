import { Component, inject, OnInit, OnDestroy, signal } from '@angular/core';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { MatProgressBarModule } from '@angular/material/progress-bar';
import { ChatService } from '../../core/services/chat.service';
import { SessionService } from '../../core/services/session.service';
import { PipelineService } from '../../core/services/pipeline.service';
import { ApiService } from '../../core/services/api.service';
import { MessageListComponent } from './components/message-list.component';
import { ChatInputComponent } from './components/chat-input.component';
import { ResumeUploadComponent } from '../resume/resume-upload.component';

type ChatState = 'welcome' | 'awaiting_resume' | 'running' | 'awaiting_input' | 'results';

@Component({
  selector: 'jobaid-chat-page',
  standalone: true,
  imports: [
    MessageListComponent,
    ChatInputComponent,
    ResumeUploadComponent,
    MatSnackBarModule,
    MatProgressBarModule
  ],
  template: `
    <div class="chat-page">
      <jobaid-message-list
        [messages]="chat.messages()"
        [isTyping]="chat.isTyping()"
        [typingMessage]="typingMessage"
      ></jobaid-message-list>

      @if (state === 'running') {
        <div class="progress-section">
          <div class="progress-info">
            <span class="progress-label">{{ typingMessage }}</span>
            <span class="progress-value">{{ pipelineProgress() }}%</span>
          </div>
          <mat-progress-bar mode="determinate" [value]="pipelineProgress()"></mat-progress-bar>
        </div>
      }

      @if (state === 'awaiting_resume') {
        <div class="upload-section">
          <jobaid-resume-upload
            (fileUploaded)="onFileUploaded($event)"
            (textPasted)="onResumePasted($event)"
          ></jobaid-resume-upload>
        </div>
      }

      @if (state !== 'awaiting_resume') {
        <jobaid-chat-input
          (messageSent)="onMessageSent($event)"
          (fileSelected)="onFileUploaded($event)"
        ></jobaid-chat-input>
      }
    </div>
  `,
  styles: `
    :host {
      display: flex;
      flex-direction: column;
      flex: 1;
      overflow: hidden;
    }
    .chat-page {
      display: flex;
      flex-direction: column;
      flex: 1;
      overflow: hidden;
      max-width: 900px;
      margin: 0 auto;
      width: 100%;
    }
    .progress-section {
      padding: 12px 16px;
      background: var(--mat-sys-surface-container-low);
      border-top: 1px solid var(--mat-sys-outline-variant);
      display: flex;
      flex-direction: column;
      gap: 8px;
    }
    .progress-info {
      display: flex;
      justify-content: space-between;
      align-items: center;
      font-size: 0.85rem;
      font-weight: 500;
      color: var(--mat-sys-on-surface-variant);
    }
    .progress-label {
      text-transform: capitalize;
    }
    .upload-section {
      padding: 0 16px 8px;
      flex-shrink: 0;
    }
    @media (max-width: 768px) {
      .chat-page {
        max-width: 100%;
      }
    }
  `,
})
export class ChatPageComponent implements OnInit, OnDestroy {
  protected readonly chat = inject(ChatService);
  private readonly session = inject(SessionService);
  private readonly pipeline = inject(PipelineService);
  private readonly api = inject(ApiService);
  private readonly snackBar = inject(MatSnackBar);

  state: ChatState = 'welcome';
  typingMessage = 'Analyzing...';
  pipelineProgress = signal(0);
  private resumeText = '';
  private progressInterval?: any;

  ngOnInit(): void {
    this.chat.clear();
    this.chat.addWelcome();
    this.state = 'awaiting_resume';
    this.typingMessage = 'Analyzing...';
    this.pipelineProgress.set(0);

    // Health check
    this.api.healthCheck().subscribe({
      error: () => this.chat.addError('Unable to connect to the backend. Please ensure the server is running on localhost:8000.'),
    });
  }

  ngOnDestroy(): void {
    this.pipeline.stopPolling();
    this.stopProgressTrickle();
  }

  async onFileUploaded(file: File): Promise<void> {
    this.resetForNewResume();

    this.chat.setTyping(true);

    try {
      const sessionId = await this.session.ensureSession();

      this.api.uploadResume(sessionId, file).subscribe({
        next: (res) => {
          this.chat.setTyping(false);
          this.resumeText = res.resume_text;
          this.chat.addResumeMessage(res.resume_text, file.name);
          this.startParsing();
        },
        error: (err) => {
          this.chat.setTyping(false);
          this.chat.addError(err?.error?.detail || 'Failed to upload resume.\nPlease try again.');
          this.state = 'awaiting_resume';
        },
      });
    } catch {
      this.chat.setTyping(false);
      this.chat.addError('Failed to create session.\nIs the backend running?');
      this.state = 'awaiting_resume';
    }
  }

  private resetForNewResume(): void {
    this.pipeline.stopPolling();
    this.chat.clear();
    this.chat.addWelcome();
    this.state = 'awaiting_resume';
    this.resumeText = '';
    this.session.clear();
  }
  async onResumePasted(text: string): Promise<void> {
    if (this.state !== 'awaiting_resume') return;

    this.resumeText = text;
    this.chat.addResumeMessage(text, 'Pasted text');
    this.startParsing();
  }

  async onMessageSent(text: string): Promise<void> {
    this.chat.addUserText(text);

    if (this.state === 'awaiting_input') {
      await this.sendConversationalStep(text);
      return;
    }

    if (this.state === 'results') {
      // Allow continuing conversation from results state
      if (this.resumeText) {
        this.state = 'awaiting_input';
        await this.sendConversationalStep(text);
      }
    }
  }

  private async startParsing(): Promise<void> {
    this.state = 'running';
    this.chat.setTyping(true);
    this.pipelineProgress.set(10);

    try {
      const sessionId = await this.session.ensureSession();
      this.session.updateStatus('running');
      this.typingMessage = 'Parsing resume...';

      this.pipeline.startPipeline(
        sessionId,
        {
          resume_text: this.resumeText,
          job_query: '',
        },
        {
          onStageChange: (status) => {
            switch (status.current_stage) {
              case 'parsing':
                this.typingMessage = 'Parsing resume...';
                this.startProgressTrickle(10, 25);
                break;
              case 'discovery':
                this.typingMessage = 'Finding matching jobs...';
                this.startProgressTrickle(25, 45);
                break;
              case 'market_intel':
                this.typingMessage = 'Analyzing market trends...';
                this.startProgressTrickle(45, 65);
                break;
              case 'pitching':
                this.typingMessage = 'Crafting your profile...';
                this.startProgressTrickle(65, 85);
                break;
              case 'summarizing':
                this.typingMessage = 'Wrapping up...';
                this.startProgressTrickle(85, 98);
                break;
              default:
                this.typingMessage = 'Working...';
                break;
            }
          },
          onAwaitingInput: (results) => {
            this.chat.setTyping(false);
            this.state = 'awaiting_input';
            this.session.updateStatus('awaiting_input');
            this.stopProgressTrickle();
            this.pipelineProgress.set(100);

            // Use completed stages from backend if available, fallback to manual calculation
            const completed = results.completed_stages || results.results.map(r => r.action);
            if (results.resume_info && !completed.includes('parsing')) completed.push('parsing');

            // Build a greeting from parsed resume data
            const resumeInfo = results.resume_info as Record<string, any> | undefined;
            if (resumeInfo) {
              const name = resumeInfo['contact_info']?.['name'] || 'there';
              const skills = (resumeInfo['skills']?.['technical'] || []).slice(0, 5);
              let greeting = `Great, I've parsed your resume, ${name}!`;
              if (skills.length > 0) {
                greeting += ` I can see you have experience with ${skills.join(', ')}.`;
              }
              greeting += '\n\nWhat would you like to do? You can ask me to:\n- Search for jobs (e.g., "Find Python developer jobs in Singapore")\n- Analyze market trends (e.g., "What\'s the fintech job market like?")\n- Write a cover letter (after finding jobs)\n- Summarize your session results';
              this.chat.addSystemText(greeting, completed);
            } else {
              this.chat.addSystemText(
                'Resume parsed! What would you like to do? Try asking me to search for jobs, analyze the market, or write a cover letter.',
                completed
              );
            }
          },
          onComplete: (results) => {
            // Shouldn't happen with the new /run, but handle gracefully
            this.chat.setTyping(false);
            this.chat.addResults(results, results.last_action || '');
            this.state = 'results';
            this.session.updateStatus('complete');
          },
          onError: (error) => {
            this.chat.setTyping(false);
            this.chat.addError(`Error parsing resume: ${error}`);
            this.state = 'awaiting_resume';
            this.session.updateStatus('error');
            this.stopProgressTrickle();
          },
        },
      );
    } catch {
      this.chat.setTyping(false);
      this.chat.addError('Failed to start parsing. Please try again.');
      this.state = 'awaiting_resume';
    }
  }

  private async sendConversationalStep(text: string): Promise<void> {
    this.chat.setTyping(true);
    this.typingMessage = 'Thinking...';
    this.state = 'running'; // Ensure progress bar shows
    this.startProgressTrickle(0, 90);
    let lastAction = '';
    let completedStages: string[] = [];

    try {
      const sessionId = await this.session.ensureSession();

      this.pipeline.sendStep(sessionId, text, {
        onResponse: (stepResponse) => {
          lastAction = stepResponse.action;
          completedStages = stepResponse.completed_stages;

          // Show the bot's response text
          if (stepResponse.response_text) {
            this.chat.addSystemText(stepResponse.response_text, completedStages);
          }

          if (stepResponse.action === 'chitchat') {
            this.chat.setTyping(false);
            this.state = 'awaiting_input';
            this.stopProgressTrickle();
          }
          // If an agent is running, typing indicator stays on until poll completes
        },
        onAwaitingInput: (results) => {
          this.chat.setTyping(false);
          this.stopProgressTrickle();
          this.pipelineProgress.set(100);
          // Show the latest result entry filtered by action
          const action = lastAction || results.last_action || '';
          const finalStages = results.completed_stages || completedStages;
          this.chat.addResults(results, action, finalStages);
          this.state = 'awaiting_input';
        },
        onError: (error) => {
          this.chat.setTyping(false);
          this.stopProgressTrickle();
          this.chat.addError(`Error: ${error}`);
          this.state = 'awaiting_input';
        },
      });
    } catch {
      this.chat.setTyping(false);
      this.stopProgressTrickle();
      this.chat.addError('Failed to send message. Please try again.');
    }
  }

  private startProgressTrickle(start: number, end: number): void {
    this.stopProgressTrickle();
    this.pipelineProgress.set(start);

    // Increment progress by 1% every 800ms, up to 'end'
    this.progressInterval = setInterval(() => {
      const current = this.pipelineProgress();
      if (current < end) {
        this.pipelineProgress.set(current + 1);
      }
    }, 800);
  }

  private stopProgressTrickle(): void {
    if (this.progressInterval) {
      clearInterval(this.progressInterval);
      this.progressInterval = undefined;
    }
  }
}
