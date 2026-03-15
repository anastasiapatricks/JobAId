import { HttpInterceptorFn } from '@angular/common/http';
import { inject } from '@angular/core';
import { tap, catchError, throwError } from 'rxjs';
import { LoggingService } from '../services/logging.service';

export const loggingInterceptor: HttpInterceptorFn = (req, next) => {
  // Don't log telemetry requests to avoid infinite loop
  if (req.url.includes('/api/telemetry')) {
    return next(req);
  }

  const log = inject(LoggingService);
  const start = Date.now();

  return next(req).pipe(
    tap((event) => {
      if ('status' in event) {
        const duration = Date.now() - start;
        if (duration > 5000) {
          log.warn('Slow HTTP request', {
            url: req.url,
            method: req.method,
            duration_ms: duration,
            status: event.status,
          });
        }
      }
    }),
    catchError((error) => {
      const duration = Date.now() - start;
      log.error('HTTP error', {
        url: req.url,
        method: req.method,
        status: error.status,
        duration_ms: duration,
        error_body: JSON.stringify(error.error)?.slice(0, 500),
      });
      return throwError(() => error);
    }),
  );
};
