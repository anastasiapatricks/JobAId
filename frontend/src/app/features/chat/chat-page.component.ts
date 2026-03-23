import { Component, inject, OnInit, OnDestroy, signal } from '@angular/core';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { MatProgressBarModule } from '@angular/material/progress-bar';
import { MatSidenavModule } from '@angular/material/sidenav';
import { ChatService } from '../../core/services/chat.service';
import { SessionService } from '../../core/services/session.service';
import { PipelineService } from '../../core/services/pipeline.service';
import { ApiService } from '../../core/services/api.service';
import { LoggingService } from '../../core/services/logging.service';
import { XaiDrawerService } from '../../core/services/xai-drawer.service';
import { MessageListComponent } from './components/message-list.component';
import { ChatInputComponent } from './components/chat-input.component';
import { ResumeUploadComponent } from '../resume/resume-upload.component';
import { AgentSidebarComponent } from './components/agent-sidebar.component';
import { ExplainabilityPageComponent } from '../explainability/explainability-page.component';

type ChatState = 'welcome' | 'awaiting_resume' | 'running' | 'awaiting_input' | 'results';

@Component({
  selector: 'jobaid-chat-page',
  standalone: true,
  imports: [
    MessageListComponent,
    ChatInputComponent,
    ResumeUploadComponent,
    AgentSidebarComponent,
    ExplainabilityPageComponent,
    MatSnackBarModule,
    MatProgressBarModule,
    MatSidenavModule
  ],
  template: `
    <mat-sidenav-container class="sidenav-container">

      <mat-sidenav
        #xaiSidenav
        mode="over"
        position="end"
        [opened]="xaiDrawer.isOpen()"
        (closedStart)="xaiDrawer.close()"
        class="xai-sidenav"
      >
        <jobaid-explainability-panel></jobaid-explainability-panel>
      </mat-sidenav>

      <mat-sidenav-content>
        <div class="chat-layout">
          <jobaid-agent-sidebar></jobaid-agent-sidebar>

          <div class="chat-page">
            <jobaid-message-list
              [messages]="chat.messages()"
              [isTyping]="chat.isTyping()"
              [typingMessage]="typingMessage"
              (suggestionClicked)="onSuggestionClicked($event)"
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
        </div>
      </mat-sidenav-content>

    </mat-sidenav-container>
  `,
  styles: `
    :host {
      display: flex;
      flex-direction: column;
      flex: 1;
      overflow: hidden;
    }
    .sidenav-container {
      flex: 1;
      height: 100%;
    }
    mat-sidenav-content {
      display: flex;
      flex-direction: column;
      height: 100%;
    }
    .xai-sidenav {
      width: 420px;
      max-width: 90vw;
    }
    .chat-layout {
      display: flex;
      flex-direction: row;
      flex: 1;
      height: 100%;
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
      position: relative;
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
    @media (max-width: 900px) {
      .chat-page {
        max-width: 100%;
      }
    }
  `,
})
export class ChatPageComponent implements OnInit, OnDestroy {
  protected readonly chat = inject(ChatService);
  protected readonly xaiDrawer = inject(XaiDrawerService);
  private readonly session = inject(SessionService);
  private readonly pipeline = inject(PipelineService);
  private readonly api = inject(ApiService);
  private readonly snackBar = inject(MatSnackBar);
  private readonly log = inject(LoggingService);

  state: ChatState = 'welcome';
  typingMessage = 'Analyzing...';
  pipelineProgress = signal(0);
  private resumeText = '';
  private progressInterval?: any;

  ngOnInit(): void {
    // If a session is already active, restore state instead of wiping the chat
    const status = this.session.sessionStatus();
    if (this.session.hasSession() && status !== 'none' && status !== 'error') {
      this.resumeText = ''; // resumeText is in-memory only; pipeline already has it
      if (status === 'running') {
        this.state = 'running';
      } else if (status === 'awaiting_input') {
        this.state = 'awaiting_input';
      } else if (status === 'complete') {
        this.state = 'results';
      }
      return;
    }

    this.chat.clear();
    this.chat.addWelcome();
    this.state = 'awaiting_resume';
    this.typingMessage = 'Analyzing...';
    this.pipelineProgress.set(0);

    this.api.healthCheck().subscribe({
      error: () => this.chat.addError(
        'Unable to connect to the backend. Please ensure the server is running on localhost:8000.'
      ),
    });
  }

  ngOnDestroy(): void {
    this.pipeline.stopPolling();
    this.stopProgressTrickle();
  }

  async onFileUploaded(file: File): Promise<void> {
    this.resetForNewResume();

    this.log.info('Resume file upload started', { filename: file.name, size: file.size });
    this.chat.setTyping(true);

    try {
      const sessionId = await this.session.ensureSession();

      this.api.uploadResume(sessionId, file).subscribe({
        next: (res) => {
          this.log.info('Resume upload complete', { text_length: res.resume_text.length });
          this.chat.setTyping(false);
          this.resumeText = res.resume_text;
          this.chat.addResumeMessage(res.resume_text, file.name);
          this.startParsing();
        },
        error: (err) => {
          this.log.error('Resume upload failed', { error: err?.error?.detail });
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
    this.resetForNewResume();
    this.resumeText = text;
    this.chat.addResumeMessage(text, 'Pasted text');
    this.startParsing();
  }

  private generateJobSuggestions(resumeInfo: Record<string, any>): string[] {
    const suggestions: string[] = [];
    const seen = new Set<string>();

    const addSuggestion = (text: string) => {
      const clean = text.trim();
      const key = clean.toLowerCase();
      if (clean && !seen.has(key)) {
        seen.add(key);
        suggestions.push(clean);
      }
    };

    // 1) Experience titles first — most relevant
    const experience = resumeInfo['experience'] || [];
    for (const exp of experience) {
      const rawTitle = (exp['title'] || '').toLowerCase().trim();
      if (!rawTitle) continue;

      const cleanTitle = rawTitle
        .replace(/\b(senior|junior|lead|principal|staff|assistant|intern|deputy)\b/gi, '')
        .replace(/\s+/g, ' ')
        .trim();

      if (cleanTitle.length > 3) {
        addSuggestion(`Find ${cleanTitle} roles in Singapore`);
      }

      if (suggestions.length >= 5) {
        return suggestions.slice(0, 5);
      }
    }

    // 2) Skills to jobs — second most relevant
    const technicalSkills = (resumeInfo['skills']?.['technical'] || [])
      .map((s: string) => s.toLowerCase().trim());

    const skillToJobMap: Record<string, string> = {
      java: 'Find Java developer roles in Singapore',
      python: 'Find Python developer roles in Singapore',
      javascript: 'Find JavaScript developer roles in Singapore',
      typescript: 'Find TypeScript developer roles in Singapore',
      react: 'Find React developer roles in Singapore',
      angular: 'Find Angular developer roles in Singapore',
      'spring boot': 'Find backend developer roles in Singapore',
      'node.js': 'Find Node.js developer roles in Singapore',
      nodejs: 'Find Node.js developer roles in Singapore',
      aws: 'Find cloud engineer roles in Singapore',
      azure: 'Find cloud engineer roles in Singapore',
      gcp: 'Find cloud engineer roles in Singapore',
      docker: 'Find DevOps engineer roles in Singapore',
      kubernetes: 'Find platform engineer roles in Singapore',
      terraform: 'Find infrastructure engineer roles in Singapore',
      sql: 'Find data analyst roles in Singapore',
      excel: 'Find business analyst roles in Singapore',
      tableau: 'Find BI analyst roles in Singapore',
      'power bi': 'Find BI analyst roles in Singapore',
      powerbi: 'Find BI analyst roles in Singapore',
      spark: 'Find data engineer roles in Singapore',
      airflow: 'Find data engineer roles in Singapore',
      kafka: 'Find data engineer roles in Singapore',
      tensorflow: 'Find machine learning engineer roles in Singapore',
      pytorch: 'Find machine learning engineer roles in Singapore',
      flutter: 'Find mobile developer roles in Singapore',
      dart: 'Find Flutter developer roles in Singapore',
      marketing: 'Find marketing roles in Singapore',
      seo: 'Find digital marketing roles in Singapore',
      accounting: 'Find accounting roles in Singapore',
      finance: 'Find finance roles in Singapore',
      recruiting: 'Find recruiter roles in Singapore',
      recruitment: 'Find recruiter roles in Singapore',
      hr: 'Find HR roles in Singapore',
      'customer service': 'Find customer service roles in Singapore',
      sales: 'Find sales roles in Singapore',
      logistics: 'Find logistics roles in Singapore',
      procurement: 'Find procurement roles in Singapore',
      nursing: 'Find nursing roles in Singapore',
      teaching: 'Find teaching roles in Singapore',
      training: 'Find trainer roles in Singapore',
      photoshop: 'Find graphic designer roles in Singapore',
      illustrator: 'Find graphic designer roles in Singapore',
      autocad: 'Find engineering roles in Singapore',
      jira: 'Find project coordinator roles in Singapore',
      postman: 'Find QA roles in Singapore',
    };

    for (const skill of technicalSkills) {
      const mapped = skillToJobMap[skill];
      if (mapped) {
        addSuggestion(mapped);
      }

      if (suggestions.length >= 5) {
        return suggestions.slice(0, 5);
      }
    }

    // 3) Summary domain keywords — broader matching
    const summary = (resumeInfo['professional_summary'] || '').toLowerCase();

    const domainKeywordMap: Record<string, string> = {
      // Cybersecurity / IT
      'malware analysis': 'Find malware analyst roles in Singapore',
      'incident response': 'Find incident response roles in Singapore',
      'digital forensics': 'Find digital forensics roles in Singapore',
      'threat intelligence': 'Find threat intelligence roles in Singapore',
      'penetration testing': 'Find penetration tester roles in Singapore',
      'cybersecurity': 'Find cybersecurity roles in Singapore',
      'security operations': 'Find security operations roles in Singapore',
      'security analyst': 'Find security analyst roles in Singapore',
      'cloud security': 'Find cloud security roles in Singapore',
      'network security': 'Find network security roles in Singapore',
      'technical support': 'Find technical support roles in Singapore',
      helpdesk: 'Find helpdesk roles in Singapore',

      // Software / Data / AI
      'software engineering': 'Find software engineer roles in Singapore',
      'software development': 'Find software developer roles in Singapore',
      backend: 'Find backend developer roles in Singapore',
      frontend: 'Find frontend developer roles in Singapore',
      'full stack': 'Find full stack developer roles in Singapore',
      'full-stack': 'Find full stack developer roles in Singapore',
      'web development': 'Find web developer roles in Singapore',
      'mobile development': 'Find mobile developer roles in Singapore',
      'data science': 'Find data scientist roles in Singapore',
      'data analysis': 'Find data analyst roles in Singapore',
      'data analytics': 'Find data analyst roles in Singapore',
      'business intelligence': 'Find business intelligence roles in Singapore',
      'data engineering': 'Find data engineer roles in Singapore',
      'machine learning': 'Find machine learning engineer roles in Singapore',
      'artificial intelligence': 'Find AI roles in Singapore',
      devops: 'Find DevOps engineer roles in Singapore',
      'cloud architecture': 'Find cloud architect roles in Singapore',
      'cloud engineering': 'Find cloud engineer roles in Singapore',
      'platform engineering': 'Find platform engineer roles in Singapore',
      'site reliability engineering': 'Find site reliability engineer roles in Singapore',
      sre: 'Find site reliability engineer roles in Singapore',

      // Product / Project / Business
      'product management': 'Find product manager roles in Singapore',
      'project management': 'Find project manager roles in Singapore',
      'program management': 'Find program manager roles in Singapore',
      'scrum master': 'Find Scrum Master roles in Singapore',
      'business analysis': 'Find business analyst roles in Singapore',
      'business analyst': 'Find business analyst roles in Singapore',
      'operations management': 'Find operations roles in Singapore',
      strategy: 'Find strategy roles in Singapore',
      consulting: 'Find consultant roles in Singapore',
      'customer success': 'Find customer success roles in Singapore',
      'account management': 'Find account manager roles in Singapore',
      'sales operations': 'Find sales operations roles in Singapore',

      // Finance / Accounting / Banking
      'financial analysis': 'Find financial analyst roles in Singapore',
      finance: 'Find finance roles in Singapore',
      accounting: 'Find accounting roles in Singapore',
      audit: 'Find audit roles in Singapore',
      taxation: 'Find tax roles in Singapore',
      'investment analysis': 'Find investment analyst roles in Singapore',
      'risk management': 'Find risk management roles in Singapore',
      compliance: 'Find compliance roles in Singapore',
      'banking operations': 'Find banking operations roles in Singapore',
      'insurance operations': 'Find insurance operations roles in Singapore',

      // Marketing / Communications
      marketing: 'Find marketing roles in Singapore',
      'digital marketing': 'Find digital marketing roles in Singapore',
      'brand management': 'Find brand manager roles in Singapore',
      'content marketing': 'Find content marketing roles in Singapore',
      'social media marketing': 'Find social media marketing roles in Singapore',
      communications: 'Find communications roles in Singapore',
      'public relations': 'Find public relations roles in Singapore',
      seo: 'Find SEO roles in Singapore',
      sem: 'Find SEM roles in Singapore',
      'market research': 'Find market research roles in Singapore',

      // HR / Admin / Legal
      'human resources': 'Find HR roles in Singapore',
      'talent acquisition': 'Find talent acquisition roles in Singapore',
      recruitment: 'Find recruiter roles in Singapore',
      'learning and development': 'Find learning and development roles in Singapore',
      'office administration': 'Find office administration roles in Singapore',
      'executive assistant': 'Find executive assistant roles in Singapore',
      'legal support': 'Find legal support roles in Singapore',
      'contract management': 'Find contract management roles in Singapore',

      // Design / Creative
      'ux design': 'Find UX designer roles in Singapore',
      'ui design': 'Find UI designer roles in Singapore',
      'graphic design': 'Find graphic designer roles in Singapore',
      'product design': 'Find product designer roles in Singapore',
      'content creation': 'Find content creator roles in Singapore',
      'video editing': 'Find video editor roles in Singapore',
      'instructional design': 'Find instructional designer roles in Singapore',

      // Supply chain / Logistics / Operations
      'supply chain': 'Find supply chain roles in Singapore',
      procurement: 'Find procurement roles in Singapore',
      logistics: 'Find logistics roles in Singapore',
      'inventory management': 'Find inventory management roles in Singapore',
      'warehouse operations': 'Find warehouse operations roles in Singapore',
      operations: 'Find operations roles in Singapore',
      'quality assurance': 'Find quality assurance roles in Singapore',

      // Healthcare / Education / Public service
      nursing: 'Find nursing roles in Singapore',
      'patient care': 'Find patient care roles in Singapore',
      pharmacy: 'Find pharmacy roles in Singapore',
      'healthcare administration': 'Find healthcare administration roles in Singapore',
      teaching: 'Find teaching roles in Singapore',
      'curriculum development': 'Find curriculum development roles in Singapore',
      training: 'Find trainer roles in Singapore',
      'public policy': 'Find public policy roles in Singapore',
      'social work': 'Find social work roles in Singapore',

      // Hospitality / Retail / Service
      hospitality: 'Find hospitality roles in Singapore',
      'customer service': 'Find customer service roles in Singapore',
      'retail operations': 'Find retail operations roles in Singapore',
      'restaurant management': 'Find restaurant manager roles in Singapore',
      'event management': 'Find event management roles in Singapore',
      'travel operations': 'Find travel operations roles in Singapore',

      // Engineering / Technical non-software
      'mechanical engineering': 'Find mechanical engineer roles in Singapore',
      'electrical engineering': 'Find electrical engineer roles in Singapore',
      'civil engineering': 'Find civil engineer roles in Singapore',
      'industrial engineering': 'Find industrial engineer roles in Singapore',
      manufacturing: 'Find manufacturing roles in Singapore',
      'process engineering': 'Find process engineer roles in Singapore',
      'quality control': 'Find quality control roles in Singapore',
    };

    for (const keyword of Object.keys(domainKeywordMap)) {
      if (summary.includes(keyword)) {
        addSuggestion(domainKeywordMap[keyword]);
      }

      if (suggestions.length >= 5) {
        return suggestions.slice(0, 5);
      }
    }

    // 4) Smart fallback
    addSuggestion('Find jobs matching my resume in Singapore');
    addSuggestion('Find mid-career roles in Singapore');
    addSuggestion('Find entry-level roles in Singapore');

    return suggestions.slice(0, 5);
  }

  onSuggestionClicked(suggestion: string): void {
    this.onMessageSent(suggestion);
  }

  async onMessageSent(text: string): Promise<void> {
    this.chat.addUserText(text);

    if (this.state === 'awaiting_input') {
      await this.sendConversationalStep(text);
      return;
    }

    if (this.state === 'results') {
      if (this.resumeText) {
        this.state = 'awaiting_input';
        await this.sendConversationalStep(text);
      }
    }
  }

  private async startParsing(): Promise<void> {
    this.log.info('Parsing started');
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
            this.chat.setCurrentStage(status.current_stage);
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
            this.log.info('Parsing complete, awaiting input');
            this.chat.setCurrentStage(null);
            this.chat.setTyping(false);
            this.state = 'awaiting_input';
            this.session.updateStatus('awaiting_input');
            this.stopProgressTrickle();
            this.pipelineProgress.set(100);

            const completed = results.completed_stages || results.results.map((r: any) => r.action);
            if (results.resume_info && !completed.includes('parsing')) {
              completed.push('parsing');
            }

            const resumeInfo = results.resume_info as Record<string, any> | undefined;

            if (resumeInfo) {
              const name = resumeInfo['contact_info']?.['name'] || 'there';
              const skills = (resumeInfo['skills']?.['technical'] || []).slice(0, 5);

              let greeting = `Great, I've parsed your resume, ${name}!`;
              if (skills.length > 0) {
                greeting += ` I can see you have experience with ${skills.join(', ')}.`;
              }

              greeting +=
                '\n\nWhat would you like to do? You can use a quick action, select a suggested role, or enter your own search in the chat box.';

              const actionSuggestions = [
                'Find jobs for my profile',
                'Analyze market trends for my profile',
                'Write a cover letter for a matched job',
                'Summarize my session results',
              ];

              const jobSuggestions = this.generateJobSuggestions(resumeInfo);

              const msg: any = {
                type: 'text',
                sender: 'system',
                text: greeting,
                completedStages: completed,
                suggestions: [...actionSuggestions, ...jobSuggestions].slice(0, 9),
              };

              this.chat['addMessage'](msg);
            } else {
              this.chat.addSystemText(
                'Resume parsed! What would you like to do next?',
                completed
              );
            }
          },
          onComplete: (results) => {
            this.chat.setTyping(false);
            this.chat.addResults(results, results.last_action || '');
            this.state = 'results';
            this.session.updateStatus('complete');
          },
          onError: (error) => {
            this.log.error('Parsing error', { error });
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
    this.log.info('Step send', { message: text.slice(0, 200) });
    this.chat.setTyping(true);
    this.typingMessage = 'Thinking...';
    this.state = 'running';
    this.startProgressTrickle(0, 90);

    let lastAction = '';
    let completedStages: string[] = [];

    try {
      const sessionId = await this.session.ensureSession();

      this.pipeline.sendStep(sessionId, text, {
        onResponse: (stepResponse) => {
          this.log.info('Step response', { action: stepResponse.action });
          lastAction = stepResponse.action;
          completedStages = stepResponse.completed_stages;

          if (stepResponse.response_text) {
            this.chat.addSystemText(stepResponse.response_text, completedStages);
          }

          if (stepResponse.action === 'chitchat') {
            this.chat.setTyping(false);
            this.state = 'awaiting_input';
            this.stopProgressTrickle();
          }
        },
        onAwaitingInput: (results) => {
          this.chat.setCurrentStage(null);
          this.chat.setTyping(false);
          this.stopProgressTrickle();
          this.pipelineProgress.set(100);

          const action = results.last_action || lastAction || '';
          const finalStages = results.completed_stages || completedStages;
          this.chat.addResults(results, action, finalStages);

          if (action === 'discovery') {
            const disc = results.results?.filter((r: any) => r.action === 'discovery') || [];
            if (disc.length > 0) {
              const discEntry = disc[disc.length - 1] as any;
              const scored: any[] = discEntry.scored_jobs || [];
              const quality: string = discEntry.result_quality || 'good';
              const originalQuery: string = discEntry.original_query || '';
              const reformulated: boolean = (discEntry.fallback_used || []).includes('query_reformulated');

              if (quality === 'poor') {
                const resumeInfo = results.resume_info as any || {};
                const exp = resumeInfo.experience || [];
                const title = resumeInfo.desired_job_title || resumeInfo.current_title
                  || (exp[0]?.title || '');
                const tech: string[] = resumeInfo.skills?.technical || [];
                const searchChips: string[] = [];
                if (title) searchChips.push(`Find ${title} roles in Singapore`);
                tech.slice(0, 2).forEach((s: string) => searchChips.push(`Find ${s} jobs in Singapore`));
                searchChips.push('Find cybersecurity jobs in Singapore');

                const msg: any = {
                  type: 'text',
                  sender: 'system',
                  text: `I searched for "${originalQuery}" but the job board didn't return strong matches for that query in Singapore — the results shown are the closest available. Try one of the searches below for better results:`,
                  suggestions: searchChips.slice(0, 5),
                  completedStages: finalStages,
                };
                this.chat['addMessage'](msg);
              } else {
                const prefix = reformulated ? 'I refined the search to better match your profile. ' : '';
                const goodJobs = scored.filter((j: any) => j.score > 0).slice(0, 5);
                const jobChips = goodJobs.map((j: any) => `I'm interested in ${j.title} at ${j.company}`);
                const msg: any = {
                  type: 'text',
                  sender: 'system',
                  text: `${prefix}Which role interests you? I'll show you the market research and then draft a cover letter.`,
                  suggestions: jobChips,
                  completedStages: finalStages,
                };
                this.chat['addMessage'](msg);
              }
            }
          } else if (action === 'market_intel') {
            const selected = results.selected_job || null;
            if (selected?.['title']) {
              // Job-specific market intel — prompt to generate cover letter
              const title: string = selected['title'] as string;
              const company: string = (selected['company'] as string) || '';
              const jobLabel = company ? `${title} at ${company}` : title;
              const msg: any = {
                type: 'text',
                sender: 'system',
                text: `Here's the market research for ${jobLabel}. Would you like me to generate a tailored cover letter for this role?`,
                suggestions: ['Yes, write the cover letter'],
                completedStages: finalStages,
              };
              this.chat['addMessage'](msg);
            } else {
              // General market intel — prompt next action
              const allResults = results.results || [];
              const discResult = [...allResults].reverse().find((r: any) => r.action === 'discovery');
              const scoredJobs: any[] = discResult?.scored_jobs || [];
              const jobChips = scoredJobs.slice(0, 3).map(
                (j: any) => `I'm interested in ${j.title} at ${j.company}`
              );
              const msg: any = {
                type: 'text',
                sender: 'system',
                text: 'Would you like to explore a specific role for a cover letter, or search for new jobs?',
                suggestions: [...jobChips, 'Find more jobs', 'Summarize my session'],
                completedStages: finalStages,
              };
              this.chat['addMessage'](msg);
            }
          } else if (action === 'pitching') {
            const msg: any = {
              type: 'text',
              sender: 'system',
              text: 'Your cover letter is ready! What would you like to do next?',
              suggestions: ['Find more jobs', 'Summarize my session', 'Pick another role'],
              completedStages: finalStages,
            };
            this.chat['addMessage'](msg);
          } else if (action === 'summarizing') {
            const msg: any = {
              type: 'text',
              sender: 'system',
              text: "That's your session summary. Would you like to search for more jobs or explore another role?",
              suggestions: ['Find more jobs', 'Find jobs for my profile'],
              completedStages: finalStages,
            };
            this.chat['addMessage'](msg);
          }

          this.state = 'awaiting_input';
        },
        onError: (error) => {
          this.log.error('Step error', { error });
          this.chat.setCurrentStage(null);
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