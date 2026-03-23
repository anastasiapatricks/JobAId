import { Pipe, PipeTransform } from '@angular/core';

/** Converts snake_case / camelCase keys into Title Case label strings. */
@Pipe({ name: 'replace', standalone: true })
export class ReplacePipe implements PipeTransform {
  transform(value: string): string {
    return value
      .replace(/_/g, ' ')
      .replace(/([a-z])([A-Z])/g, '$1 $2')
      .replace(/\b\w/g, c => c.toUpperCase());
  }
}
