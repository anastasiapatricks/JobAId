import { Component, Output, EventEmitter, HostListener } from '@angular/core';
import { MatIconModule } from '@angular/material/icon';

@Component({
  selector: 'jobaid-file-drop-zone',
  standalone: true,
  imports: [MatIconModule],
  template: `
    <div
      class="drop-zone"
      [class.dragover]="isDragOver"
      (click)="fileInput.click()"
    >
      <mat-icon class="upload-icon">cloud_upload</mat-icon>
      <p class="primary-text">Drag & drop your resume here</p>
      <p class="secondary-text">or click to browse (PDF, TXT, DOC)</p>
      <input
        #fileInput
        type="file"
        hidden
        accept=".pdf,.txt,.doc,.docx"
        (change)="onFileSelected($event)"
      />
    </div>
  `,
  styles: `
    .drop-zone {
      border: 2px dashed #93c5fd;
      border-radius: var(--app-radius-lg);
      padding: 36px 24px;
      text-align: center;
      cursor: pointer;
      transition: all 0.2s ease;
      background: linear-gradient(135deg, #0f172a 0%, #1e3a8a 100%);
      color: white;
      box-shadow: 0 10px 28px rgba(37, 99, 235, 0.18);
    }

    .drop-zone:hover,
    .drop-zone.dragover {
      border-color: #bfdbfe;
      transform: translateY(-1px);
      box-shadow: 0 14px 32px rgba(37, 99, 235, 0.24);
    }

    .upload-icon {
      font-size: 48px;
      width: 48px;
      height: 48px;
      color: #bfdbfe;
      margin-bottom: 10px;
    }

    .primary-text {
      font-weight: 700;
      margin: 8px 0 6px;
      color: white;
    }

    .secondary-text {
      font-size: 0.9rem;
      color: #dbeafe;
      margin: 0;
    }
  `,
})
export class FileDropZoneComponent {
  @Output() fileDropped = new EventEmitter<File>();
  isDragOver = false;

  @HostListener('dragover', ['$event'])
  onDragOver(event: DragEvent): void {
    event.preventDefault();
    event.stopPropagation();
    this.isDragOver = true;
  }

  @HostListener('dragleave', ['$event'])
  onDragLeave(event: DragEvent): void {
    event.preventDefault();
    event.stopPropagation();
    this.isDragOver = false;
  }

  @HostListener('drop', ['$event'])
  onDrop(event: DragEvent): void {
    event.preventDefault();
    event.stopPropagation();
    this.isDragOver = false;
    const file = event.dataTransfer?.files[0];
    if (file) {
      this.fileDropped.emit(file);
    }
  }

  onFileSelected(event: Event): void {
    const input = event.target as HTMLInputElement;
    const file = input.files?.[0];
    if (file) {
      this.fileDropped.emit(file);
      input.value = '';
    }
  }
}
