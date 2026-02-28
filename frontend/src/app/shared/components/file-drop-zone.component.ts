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
      border: 2px dashed rgba(0, 0, 0, 0.2);
      border-radius: 12px;
      padding: 32px 24px;
      text-align: center;
      cursor: pointer;
      transition: all 0.2s ease;
      background: rgba(0, 0, 0, 0.02);
    }
    .drop-zone:hover,
    .drop-zone.dragover {
      border-color: var(--mat-sys-primary);
      background: rgba(var(--mat-sys-primary), 0.04);
    }
    .upload-icon {
      font-size: 48px;
      width: 48px;
      height: 48px;
      opacity: 0.5;
      margin-bottom: 8px;
    }
    .primary-text {
      font-weight: 500;
      margin: 8px 0 4px;
    }
    .secondary-text {
      font-size: 0.85rem;
      opacity: 0.6;
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
