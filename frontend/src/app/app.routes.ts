import { Routes } from '@angular/router';

export const routes: Routes = [
  {
    path: '',
    loadComponent: () =>
      import('./features/chat/chat-page.component').then((m) => m.ChatPageComponent),
  },
  {
    path: 'session/:id',
    loadComponent: () =>
      import('./features/chat/chat-page.component').then((m) => m.ChatPageComponent),
  },
  { path: '**', redirectTo: '' },
];
