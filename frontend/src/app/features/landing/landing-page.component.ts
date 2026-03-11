import { Component } from '@angular/core';
import { RouterLink } from '@angular/router';

@Component({
  selector: 'jobaid-landing-page',
  standalone: true,
  imports: [RouterLink],
  template: `
    <div class="landing-container">
      <div class="hero">
        <h1 class="title">JobAId</h1>
        <p class="tagline">Solving all your job problems with AI.</p>
        <button class="get-started" routerLink="/chat">Get Started</button>
      </div>
    </div>
  `,
  styles: `
    .landing-container {
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      height: 100vh;
      background: linear-gradient(135deg, #121212 0%, #1e1e1e 100%);
      color: white;
      text-align: center;
      font-family: 'Outfit', sans-serif;
    }
    .hero {
      max-width: 600px;
      padding: 0 20px;
    }
    .title {
      font-size: 5rem;
      font-weight: 800;
      margin-bottom: 0.5rem;
      background: linear-gradient(90deg, #4facfe 0%, #00f2fe 100%);
      -webkit-background-clip: text;
      -webkit-text-fill-color: transparent;
      background-clip: text;
      display: inline-block;
      line-height: 1.1;
      padding: 0.1em 0;
    }
    .tagline {
      font-size: 1.5rem;
      font-weight: 300;
      margin-bottom: 2rem;
      color: #b0b0b0;
    }
    .get-started {
      padding: 1rem 2rem;
      font-size: 1.25rem;
      font-weight: 600;
      color: white;
      background: #4facfe;
      border: none;
      border-radius: 50px;
      cursor: pointer;
      transition: all 0.3s ease;
      box-shadow: 0 4px 15px rgba(79, 172, 254, 0.4);
    }
    .get-started:hover {
      background: #00f2fe;
      transform: translateY(-2px);
      box-shadow: 0 6px 20px rgba(0, 242, 254, 0.6);
    }
    .get-started:active {
      transform: translateY(0);
    }
  `,
})
export class LandingPageComponent { }
