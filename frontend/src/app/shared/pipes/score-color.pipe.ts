import { Pipe, PipeTransform } from '@angular/core';

@Pipe({ name: 'scoreColor', standalone: true })
export class ScoreColorPipe implements PipeTransform {
  transform(score: number): string {
    if (score >= 80) return 'score-high';
    if (score >= 60) return 'score-medium';
    return 'score-low';
  }
}
