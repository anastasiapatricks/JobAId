# Job Connect Demo (LangGraph Multi-Agent)
 
A hands-on demonstration of a **multi-agent job search assistant**, built using **LangGraph** and **LangChain**, that parses resumes, finds relevant jobs, scores them, and generates a personalized job pitch; all in one conversational flow.
 
## Overview
 

This project simulates a multi-agent job search pipeline, where each agent performs a distinct step:

| Agent              | Responsibility |
|--------------------|----------------|
| **Human Node**     | Accepts user input (resume file, job query, exit command). |
| **Resume Parser**  | Extracts skills and experience from a given resume text. Adds a summary message to the state. |
| **Job Search**     | Searches mock job listings that match extracted skills and query. Adds a debug and result message to the state. |
| **Relevance Scorer** | Scores and ranks top jobs by skill overlap. Adds a summary message to the state. |
| **Pitch Generator** | Crafts a tailored pitch for the best-matched role, using Wikipedia info if available. Adds debug and result messages to the state. |
| **Summarizer**     | Summarizes the overall agent conversation and outcomes, using all accumulated messages. |

**Debug Logging:**
- Each agent step adds debug messages to the state for traceability. These are included in the conversation history and can be used for troubleshooting or summary generation.
- The Wikipedia tool logs the URL, status code, and fallback logic for company info lookups.

**Wikipedia Integration:**
- The pitch generator uses a robust Wikipedia summary tool that tries direct, (company), (organisation), and (organization) lookups via the Wikipedia REST API.
- Debug logs are included for all Wikipedia fetch attempts.

**Summary Troubleshooting:**
- The summarizer prints all messages and the constructed conversation text before summarizing, so you can see exactly what is being summarized.
- If the summary fails, the exception is logged and a fallback message is shown.
 
Each run randomly selects one of 10 resume/job-query pairs for variety and realism.
 
---
 
## Architecture
 
┌──────────┐
│ START │
└────┬─────┘
│
▼
┌──────────┐ ┌────────────┐ ┌───────────────┐
│ Human │──►│ Coordinator │──►│ Participant │
└──────────┘ └────────────┘ └───────────────┘
│
▼
┌──────────────┐
│ Summarizer │
└──────────────┘
 
 
- **`State`** tracks progress: messages, agent outputs, volley count, and stage index.  
- **`Coordinator`** decides which agent runs next.  
- **`Participant`** calls the corresponding agent module.  
- **Nodes** define LangGraph node logic and transitions.  
- **`main.py`** orchestrates the demo flow.
 
---
 
## Setup Instructions
 
### 1. Clone & Install Dependencies
 
git clone https://github.com/SanathSame/NUS-ISS-ArchAASTeam4.git.
 
cd 3-workshop
uv sync
 
--
 
## 2. Setup Environment
 
OPENAI_API_KEY=your_openai_key_here
 
 
## 3. Run the Demo
 
uv run python main.py
 
You’ll see the ASCII graph and a randomly chosen resume scenario:
 
[DEMO] Using scenario:
       Resume: DevOps engineer, 7 years in Kubernetes, Terraform, AWS, GitLab CI, Prometheus, Grafana.
       Query : devops kubernetes terraform aws gitlab ci singapore
 
 

## 4. Example Output

       [COORDINATOR] Next agent: resume_parser
       [RESUME] Parsed resume.
       Parsed resume. Skills: aws, git, kubernetes. Experience: 7 yrs.
       [JOBS] Fetched job listings.
       [DEBUG] Job search returning 10 jobs. Used [TOOL] Job Scrape to find matches.
       [SCORE] Scored job listings.
       Top matches:
       1. Platform Engineer @ Cloudy — 20/100 (overlap: aws, kubernetes)
       2. Data Engineer @ Marina Analytics — 20/100 (overlap: aws, kubernetes)
       ...
       [PITCH] Generated pitch.
       [DEBUG] Tool Pitch Generator has been called.
       [DEBUG] Initial company from scored_jobs: Cloudy
       [DEBUG] Final company to use: Cloudy
       [DEBUG] Fetching Wikipedia info for company: Cloudy
       Generated a tailored pitch using Wikipedia company info. Used [TOOL] Wikipedia to fetch company summary.
       === PITCH ===
       Hi Hiring Team, I'm Candidate. I’ve worked extensively with aws, git, kubernetes and I’m excited about Platform Engineer at Cloudy... 
 

## 5. Folder Structure

3-workshop/
├── agents/
│   ├── __init__.py
│   ├── coordinator.py
│   ├── participant.py
│   ├── resume_parser.py
│   ├── job_search.py
│   ├── relevance_scorer.py
│   ├── pitch_generator.py
│   └── summarizer.py
├── nodes.py
├── state.py
├── main.py
├── utils.py
├── tools/
│   ├── __init__.py
│   ├── job_scrape.py
│   ├── wikipedia.py
│   └── test.py
├── sample_resume.txt
├── sample_resume_oth.txt
└── README.md
 
## 5. Future Enhancement
- Integrate live job APIs (LinkedIn, MyCareersFuture, Indeed)
- Add resume upload + LLM parsing using embeddings
- Extend multi-turn conversations for job filtering
- Include evaluation metrics for agent accuracy
- Build a Streamlit / Gradio web UI
 
 
## 6. Credits
 
Developed for NUS-ISS ArchAAS Workshop
Author: Sanath, Hany, Anastasia, Ke An (Team 4)
Purpose: Multi-Agent Reasoning with LangGraph