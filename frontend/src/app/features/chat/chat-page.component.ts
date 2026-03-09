import { Component, inject, OnInit, OnDestroy } from '@angular/core';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
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
  imports: [MessageListComponent, ChatInputComponent, ResumeUploadComponent, MatSnackBarModule],
  template: `
    <div class="chat-page">
      <jobaid-message-list
        [messages]="chat.messages()"
        [isTyping]="chat.isTyping()"
      ></jobaid-message-list>

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
  private resumeText = '';

  ngOnInit(): void {
    this.chat.clear();
    this.chat.addWelcome();
    this.state = 'awaiting_resume';

    // Health check
    this.api.healthCheck().subscribe({
      error: () => this.chat.addError('Unable to connect to the backend. Please ensure the server is running on localhost:8000.'),
    });
  }

  ngOnDestroy(): void {
    this.pipeline.stopPolling();
  }

  async onFileUploaded(file: File): Promise<void> {
    this.resetForNewResume();

    this.chat.addSystemText(`Uploading ${file.name}...`);
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
    this.chat.addSystemText('Parsing your resume...');

    try {
      const sessionId = await this.session.ensureSession();
      this.session.updateStatus('running');

      this.pipeline.startPipeline(
        sessionId,
        {
          resume_text: this.resumeText,
          job_query: '',
        },
        {
          onAwaitingInput: (results) => {
            this.chat.setTyping(false);
            this.state = 'awaiting_input';
            this.session.updateStatus('awaiting_input');

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
              this.chat.addSystemText(greeting);
            } else {
              this.chat.addSystemText(
                'Resume parsed! What would you like to do? Try asking me to search for jobs, analyze the market, or write a cover letter.',
              );
            }
          },
          onComplete: (results) => {
            // Shouldn't happen with the new /run, but handle gracefully
            this.chat.setTyping(false);
            this.chat.addSystemText('Analysis complete! Here are your results:');
            this.chat.addResults(results, results.last_action || '');
            this.state = 'results';
            this.session.updateStatus('complete');
          },
          onError: (error) => {
            this.chat.setTyping(false);
            this.chat.addError(`Error parsing resume: ${error}`);
            this.state = 'awaiting_resume';
            this.session.updateStatus('error');
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
    let lastAction = '';

    try {
      const sessionId = await this.session.ensureSession();

      this.pipeline.sendStep(sessionId, text, {
        onResponse: (stepResponse) => {
          lastAction = stepResponse.action;

          // Show the bot's response text
          if (stepResponse.response_text) {
            this.chat.addSystemText(stepResponse.response_text);
          }

          if (stepResponse.action === 'chitchat') {
            this.chat.setTyping(false);
            // Stay in awaiting_input
          }
          // If an agent is running, typing indicator stays on until poll completes
        },
        onAwaitingInput: (results) => {
          this.chat.setTyping(false);
          // Show the latest result entry filtered by action
          const action = lastAction || results.last_action || '';
          this.chat.addResults(results, action);
          this.state = 'awaiting_input';
        },
        onError: (error) => {
          this.chat.setTyping(false);
          this.chat.addError(`Error: ${error}`);
          this.state = 'awaiting_input';
        },
      });
    } catch {
      this.chat.setTyping(false);
      this.chat.addError('Failed to send message. Please try again.');
    }
  }
}
