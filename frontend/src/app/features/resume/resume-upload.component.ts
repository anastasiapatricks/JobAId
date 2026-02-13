import { Component, Output, EventEmitter } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { FileDropZoneComponent } from '../../shared/components/file-drop-zone.component';

@Component({
  selector: 'jobaid-resume-upload',
  standalone: true,
  imports: [FormsModule, MatButtonModule, MatFormFieldModule, MatInputModule, FileDropZoneComponent],
  template: `
    <div class="resume-upload">
      <jobaid-file-drop-zone (fileDropped)="onFile($event)"></jobaid-file-drop-zone>

      <div class="divider">
        <span>or paste your resume text</span>
      </div>

      <mat-form-field class="paste-field" appearance="outline">
        <mat-label>Paste resume text here...</mat-label>
        <textarea
          matInput
          [(ngModel)]="pastedText"
          rows="6"
        ></textarea>
      </mat-form-field>

      @if (pastedText.trim()) {
        <button mat-flat-button color="primary" (click)="submitPaste()">
          Submit Resume Text
        </button>
      }
    </div>
  `,
  styles: `
    .resume-upload {
      display: flex;
      flex-direction: column;
      gap: 16px;
      padding: 8px 0;
    }
    .divider {
      text-align: center;
      position: relative;
      margin: 8px 0;
      span {
        background: var(--mat-sys-surface);
        padding: 0 12px;
        font-size: 0.85rem;
        opacity: 0.6;
        position: relative;
        z-index: 1;
      }
      &::before {
        content: '';
        position: absolute;
        top: 50%;
        left: 0;
        right: 0;
        height: 1px;
        background: rgba(0, 0, 0, 0.12);
      }
    }
    .paste-field {
      width: 100%;
    }
  `,
})
export class ResumeUploadComponent {
  @Output() fileUploaded = new EventEmitter<File>();
  @Output() textPasted = new EventEmitter<string>();

  pastedText = '';

  onFile(file: File): void {
    this.fileUploaded.emit(file);
  }

  submitPaste(): void {
    const text = this.pastedText.trim();
    if (text) {
      this.textPasted.emit(text);
      this.pastedText = '';
    }
  }
}
