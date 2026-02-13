import { Directive, ElementRef, inject, AfterViewInit, OnDestroy, Input } from '@angular/core';

@Directive({
  selector: '[jobaidAutoScroll]',
  standalone: true,
})
export class AutoScrollDirective implements AfterViewInit, OnDestroy {
  private readonly el = inject(ElementRef);
  private observer?: MutationObserver;

  @Input() jobaidAutoScroll = true;

  ngAfterViewInit(): void {
    this.observer = new MutationObserver(() => {
      if (this.jobaidAutoScroll) {
        this.scrollToBottom();
      }
    });
    this.observer.observe(this.el.nativeElement, { childList: true, subtree: true });
  }

  scrollToBottom(): void {
    const el = this.el.nativeElement as HTMLElement;
    requestAnimationFrame(() => {
      el.scrollTop = el.scrollHeight;
    });
  }

  ngOnDestroy(): void {
    this.observer?.disconnect();
  }
}
