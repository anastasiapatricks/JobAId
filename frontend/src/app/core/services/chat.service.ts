import { Injectable, signal, computed } from '@angular/core';
import { PipelineStatusResponse } from '../models/pipeline.model';
import { PipelineResults } from '../models/results.model';

export type MessageType = 'text' | 'resume' | 'stageUpdate' | 'results' | 'error' | 'welcome';
export type MessageSender = 'user' | 'system';

export interface ChatMessage {
  id: string;
  type: MessageType;
  sender: MessageSender;
  text?: string;
  resumeText?: string;
  fileName?: string;
  stageStatus?: PipelineStatusResponse;
  results?: PipelineResults;
  action?: string;
  timestamp: Date;
}

let messageIdCounter = 0;

@Injectable({ providedIn: 'root' })
export class ChatService {
  readonly messages = signal<ChatMessage[]>([]);
  readonly isTyping = signal(false);
  readonly messageCount = computed(() => this.messages().length);

  addWelcome(): void {
    this.addMessage({
      type: 'welcome',
      sender: 'system',
      text: 'Welcome to JobAId! I\'ll help you find the best job matches, identify skill gaps, and create a personalized career roadmap.\n\nTo get started, please upload your resume (PDF or TXT) or paste your resume text below.',
    });
  }

  addUserText(text: string): void {
    this.addMessage({ type: 'text', sender: 'user', text });
  }

  addSystemText(text: string): void {
    this.addMessage({ type: 'text', sender: 'system', text });
  }

  addResumeMessage(resumeText: string, fileName?: string): void {
    this.addMessage({ type: 'resume', sender: 'user', resumeText, fileName });
  }

  addStageUpdate(status: PipelineStatusResponse): void {
    this.addMessage({ type: 'stageUpdate', sender: 'system', stageStatus: status });
  }

  addResults(results: PipelineResults, action?: string): void {
    this.addMessage({ type: 'results', sender: 'system', results, action });
  }

  addError(text: string): void {
    this.addMessage({ type: 'error', sender: 'system', text });
  }

  setTyping(typing: boolean): void {
    this.isTyping.set(typing);
  }

  clear(): void {
    this.messages.set([]);
    this.isTyping.set(false);
  }

  private addMessage(partial: Omit<ChatMessage, 'id' | 'timestamp'>): void {
    const msg: ChatMessage = {
      ...partial,
      id: `msg-${++messageIdCounter}`,
      timestamp: new Date(),
    };
    this.messages.update((msgs) => [...msgs, msg]);
  }
}
