import { Component, inject, OnInit, OnDestroy } from '@angular/core';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { ChatService } from '../../core/services/chat.service';
import { SessionService } from '../../core/services/session.service';
import { PipelineService } from '../../core/services/pipeline.service';
import { ApiService } from '../../core/services/api.service';
import { MessageListComponent } from './components/message-list.component';
import { ChatInputComponent } from './components/chat-input.component';
import { ResumeUploadComponent } from '../resume/resume-upload.component';
import { PipelineStatusResponse } from '../../core/models/pipeline.model';

type ChatState = 'welcome' | 'awaiting_resume' | 'awaiting_query' | 'running' | 'results';

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

      <jobaid-chat-input
        (messageSent)="onMessageSent($event)"
        (fileSelected)="onFileUploaded($event)"
      ></jobaid-chat-input>
    </div>
  `,
  styles: `
    .chat-page {
      display: flex;
      flex-direction: column;
      height: calc(100vh - 64px);
      max-width: 900px;
      margin: 0 auto;
      width: 100%;
    }
    .upload-section {
      padding: 0 16px 8px;
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
    if (this.state !== 'awaiting_resume') return;

    this.chat.addSystemText(`Uploading ${file.name}...`);
    this.chat.setTyping(true);

    try {
      const sessionId = await this.session.ensureSession();
      this.api.uploadResume(sessionId, file).subscribe({
        next: (res) => {
          this.chat.setTyping(false);
          this.resumeText = res.resume_text;
          this.chat.addResumeMessage(res.resume_text, file.name);
          this.promptForQuery();
        },
        error: (err) => {
          this.chat.setTyping(false);
          this.chat.addError(err?.error?.detail || 'Failed to upload resume. Please try again.');
        },
      });
    } catch {
      this.chat.setTyping(false);
      this.chat.addError('Failed to create session. Is the backend running?');
    }
  }

  async onResumePasted(text: string): Promise<void> {
    if (this.state !== 'awaiting_resume') return;

    this.resumeText = text;
    this.chat.addResumeMessage(text, 'Pasted text');
    this.promptForQuery();
  }

  async onMessageSent(text: string): Promise<void> {
    this.chat.addUserText(text);

    if (this.state === 'awaiting_resume') {
      // Treat as pasted resume text
      this.resumeText = text;
      this.chat.addResumeMessage(text);
      this.promptForQuery();
      return;
    }

    if (this.state === 'awaiting_query') {
      await this.startPipeline(text);
      return;
    }

    if (this.state === 'results') {
      // Allow starting a new query with existing resume
      if (this.resumeText) {
        await this.startPipeline(text);
      }
    }
  }

  private promptForQuery(): void {
    this.state = 'awaiting_query';
    this.chat.addSystemText(
      'Resume received! Now, what kind of job are you looking for?\n\nFor example: "Python backend engineer in Singapore" or "Data scientist with ML experience"'
    );
  }

  private async startPipeline(query: string): Promise<void> {
    this.state = 'running';
    this.chat.setTyping(true);
    this.chat.addSystemText('Starting analysis pipeline...');

    try {
      const sessionId = await this.session.ensureSession();
      this.session.updateStatus('running');

      let lastStage: string | null = null;

      this.pipeline.startPipeline(
        sessionId,
        {
          resume_text: this.resumeText,
          job_query: query,
        },
        {
          onStageChange: (status: PipelineStatusResponse) => {
            if (status.current_stage !== lastStage) {
              lastStage = status.current_stage;
              this.chat.addStageUpdate(status);
            }
          },
          onComplete: (results) => {
            this.chat.setTyping(false);
            this.chat.addSystemText('Analysis complete! Here are your results:');
            this.chat.addResults(results);
            this.state = 'results';
            this.session.updateStatus('complete');
            this.snackBar.open('Pipeline completed successfully!', 'OK', { duration: 3000 });
          },
          onError: (error) => {
            this.chat.setTyping(false);
            this.chat.addError(`Pipeline error: ${error}`);
            this.state = 'awaiting_query';
            this.session.updateStatus('error');
          },
        },
      );
    } catch {
      this.chat.setTyping(false);
      this.chat.addError('Failed to start pipeline. Please try again.');
      this.state = 'awaiting_query';
    }
  }
}
