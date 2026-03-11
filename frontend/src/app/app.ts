import { Component, inject, computed } from '@angular/core';
import { RouterOutlet, Router, NavigationEnd } from '@angular/router';
import { toSignal } from '@angular/core/rxjs-interop';
import { filter, map } from 'rxjs';
import { ToolbarComponent } from './shared/components/toolbar.component';

@Component({
  selector: 'jobaid-root',
  standalone: true,
  imports: [RouterOutlet, ToolbarComponent],
  template: `
    @if (showToolbar()) {
      <jobaid-toolbar></jobaid-toolbar>
    }
    <router-outlet></router-outlet>
  `,
  styleUrl: './app.scss',
})
export class App {
  private readonly router = inject(Router);

  private readonly currentUrl = toSignal(
    this.router.events.pipe(
      filter((e): e is NavigationEnd => e instanceof NavigationEnd),
      map(e => e.urlAfterRedirects)
    )
  );

  protected readonly showToolbar = computed(() => {
    const url = this.currentUrl();
    // Hide toolbar ONLY on landing page ('/' or empty)
    return url !== '/' && url !== '';
  });
}
