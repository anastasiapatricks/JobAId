import { Directive, ElementRef, inject, AfterViewInit, OnDestroy, Input } from '@angular/core';

@Directive({
  selector: '[jobaidAutoScroll]',
  standalone: true,
})
export class AutoScrollDirective implements AfterViewInit, OnDestroy {
  private readonly el = inject(ElementRef);
  private observer?: MutationObserver;

  @Input() jobaidAutoScroll = true;
  @Input() scrollMode: 'bottom' | 'smart' = 'bottom';

  ngAfterViewInit(): void {
    this.observer = new MutationObserver((mutations) => {
      if (!this.jobaidAutoScroll) return;

      if (this.scrollMode === 'smart') {
        const hasResults = mutations.some((m) =>
          Array.from(m.addedNodes).some(
            (n) => n instanceof HTMLElement && n.querySelector('.results-bubble')
          )
        );

        if (hasResults) {
          this.scrollToLatestResult();
          return;
        }
      }

      this.scrollToBottom();
    });
    this.observer.observe(this.el.nativeElement, { childList: true, subtree: false });
  }

  scrollToBottom(): void {
    const el = this.el.nativeElement as HTMLElement;
    requestAnimationFrame(() => {
      el.scrollTop = el.scrollHeight;
    });
  }

  private scrollToLatestResult(): void {
    const el = this.el.nativeElement as HTMLElement;
    requestAnimationFrame(() => {
      const results = el.querySelectorAll('.results-bubble');
      if (results.length > 0) {
        const lastResult = results[results.length - 1];
        lastResult.scrollIntoView({ behavior: 'smooth', block: 'start' });
      } else {
        this.scrollToBottom();
      }
    });
  }

  ngOnDestroy(): void {
    this.observer?.disconnect();
  }
}
