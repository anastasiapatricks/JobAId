# CloudWatch Logs — Search and Analysis Guide

This guide explains how to efficiently search and analyse JobAId logs using AWS CloudWatch Logs Insights and the pre-built CloudWatch Dashboard.

---

## 1. Log Architecture Overview

All application logs are structured JSON emitted to stdout/stderr and forwarded to CloudWatch via Docker's `awslogs` driver (configured in `docker-compose.prod.yml`).

| Log Group | Source | Retention |
|---|---|---|
| `/jobaid/backend` | FastAPI backend container | 7 days |
| `/jobaid/frontend` | Nginx + frontend telemetry | 7 days |

### Logger Hierarchy

| Logger Name | Source File | Events |
|---|---|---|
| `jobaid.api` | `api/middleware.py` | HTTP request/response logs |
| `jobaid.llm` | `utils/llm_logger.py` | LLM call instrumentation |
| `jobaid.frontend` | `api/routes/telemetry.py` | Frontend telemetry (batched from browser) |
| `jobaid.guardrails` | `guardrails/*.py` | Guardrail trigger events |
| `jobaid.external` | `tools/job_board_api.py`, `tools/tavily_search.py` | External API call logs (Adzuna, Tavily) |
| `jobaid.session` | `api/dependencies.py` | Session lifecycle events (create, update, delete, evict) |
| `jobaid.pipeline` | `graph/nodes.py` | Pipeline stage execution logs |
| `jobaid.debug` | `utils/__init__.py` | Debug trace logs |

---

## 2. Accessing the Dashboard

The pre-built CloudWatch Dashboard (`jobaid-dashboard`, defined in `infra/dashboard.tf`) provides 19 widgets organised into five groups:

1. **Infrastructure** — EC2 CPU utilisation, network I/O
2. **API Health** — request throughput, error rate, latency percentiles, slowest endpoints
3. **LLM Metrics** — token usage, cost by task, call errors, session summaries
4. **Pipeline & External** — stage timing, external API health (Adzuna, Tavily)
5. **Operations** — session activity, session funnel, guardrail triggers

To access: **AWS Console > CloudWatch > Dashboards > `jobaid-dashboard`**

All widgets use Logs Insights queries. Click any widget title to open the query in Logs Insights for further exploration.

---

## 3. CloudWatch Logs Insights — Common Queries

Open **CloudWatch > Logs > Logs Insights**, select the `/jobaid/backend` log group, and paste the queries below.

### 3.1 Request Tracing

**Trace a single request by request_id:**
```
fields @timestamp, @message
| filter @message like /"request_id": "ab12cd34"/
| sort @timestamp asc
```

**Trace all requests for a session:**
```
fields @timestamp, @message
| filter @message like /"session_id": "your-uuid-here"/
| sort @timestamp asc
```

This returns middleware logs, LLM calls, pipeline stages, and guardrail events — everything tied to that session — because all log layers propagate `session_id` via Python `contextvars`.

### 3.2 API Performance

**Slowest endpoints in the last hour:**
```
filter @message like /"duration"/
| parse @message '"method": "*"' as method
| parse @message '"path": "*"' as path
| parse @message '"duration": *}' as duration_sec
| filter method in ["POST","GET","PUT","DELETE","PATCH"]
| stats avg(duration_sec) as avg_s, max(duration_sec) as max_s, count(*) as calls by method, path
| sort avg_s desc
| limit 10
```

**API error rate over time (5-minute bins):**
```
filter @message like /"status"/
| parse @message '"status": *,' as status_code
| parse @message '"method": "*"' as method
| filter method in ["POST","GET","PUT","DELETE","PATCH"]
| stats sum(status_code >= 400) as errors, count(*) as total by bin(5m)
```

**Latency percentiles (p50/p90/p99):**
```
filter @message like /"duration"/
| parse @message '"duration": *}' as duration_sec
| parse @message '"method": "*"' as method
| filter method in ["POST","GET","PUT","DELETE","PATCH"]
| stats avg(duration_sec) as avg_s, pct(duration_sec, 50) as p50, pct(duration_sec, 90) as p90, pct(duration_sec, 99) as p99 by bin(5m)
```

### 3.3 LLM Call Analysis

**Token usage by agent/task type:**
```
filter @message like /llm_call/
| parse @message '"task_type": "*"' as task_type
| parse @message '"prompt_tokens": *,' as prompt_tokens
| parse @message '"completion_tokens": *,' as completion_tokens
| parse @message '"total_tokens": *,' as total_tokens
| stats sum(prompt_tokens) as prompt_tok, sum(completion_tokens) as completion_tok, sum(total_tokens) as total_tok, count(*) as calls by task_type
| sort total_tok desc
```

**LLM latency by agent:**
```
filter @message like /llm_call/
| parse @message '"task_type": "*"' as task_type
| parse @message '"latency_ms": *,' as latency_ms
| parse @message '"total_tokens": *,' as total_tokens
| stats avg(latency_ms) as avg_latency, max(latency_ms) as max_latency, sum(total_tokens) as tokens, count(*) as calls by task_type
```

**Recent LLM errors:**
```
filter @message like /llm_call/ and @message like /"error"/
| parse @message '"task_type": "*"' as task_type
| parse @message '"error": "*"' as error_msg
| parse @message '"model": "*"' as model
| parse @message '"latency_ms": *,' as latency_ms
| display @timestamp, task_type, model, latency_ms, error_msg
| sort @timestamp desc
| limit 20
```

**Session-level LLM summaries:**
```
filter @message like /llm_session_summary/
| parse @message '"session_id": "*"' as session_id
| parse @message '"total_calls": *,' as total_calls
| parse @message '"total_tokens": *,' as total_tokens
| parse @message '"total_latency_ms": *,' as total_latency_ms
| parse @message '"avg_latency_ms": *}' as avg_latency_ms
| display @timestamp, session_id, total_calls, total_tokens, total_latency_ms, avg_latency_ms
| sort @timestamp desc
| limit 20
```

### 3.4 Pipeline Stage Analysis

**Average stage timing and error rate:**
```
filter @message like /pipeline_stage/
| parse @message '"stage": "*"' as stage
| parse @message '"status": "*"' as status
| parse @message '"latency_ms": *,' as latency_ms
| stats avg(latency_ms) as avg_ms, max(latency_ms) as max_ms, sum(status = "error") as errors, count(*) as calls by stage
| sort avg_ms desc
```

**Stage latency over time:**
```
filter @message like /pipeline_stage/
| parse @message '"stage": "*"' as stage
| parse @message '"latency_ms": *,' as latency_ms
| stats avg(latency_ms) as avg_ms by stage, bin(5m)
```

### 3.5 Security and Guardrails

**Recent guardrail triggers:**
```
filter @message like /guardrail_triggered/
| parse @message '"guardrail": "*"' as guardrail
| parse @message '"stage": "*"' as stage
| parse @message '"detail": "*"' as detail
| display @timestamp, guardrail, stage, detail
| sort @timestamp desc
| limit 30
```

**Guardrail trigger counts by type:**
```
filter @message like /guardrail_triggered/
| parse @message '"guardrail": "*"' as guardrail
| stats count(*) as triggers by guardrail
| sort triggers desc
```

### 3.6 Frontend Telemetry

**Recent frontend errors (ingested via `POST /api/telemetry`):**
```
filter @message like /"event": "frontend"/ and @logStream like /backend/
| parse @message '"message": "*"' as message
| parse @message '"session_id": "*"' as session_id
| filter @message like /ERROR/
| display @timestamp, session_id, message
| sort @timestamp desc
| limit 20
```

### 3.7 External API Health

**External API success rates and latency:**
```
filter @message like /external_api_call/
| parse @message '"service": "*"' as service
| parse @message '"operation": "*"' as operation
| parse @message '"status": "*"' as status
| parse @message '"latency_ms": *,' as latency_ms
| stats avg(latency_ms) as avg_ms, max(latency_ms) as max_ms, sum(status = "error") as errors, count(*) as calls by service, operation
```

### 3.8 Session Lifecycle

**Session funnel (create → pipeline → complete → delete):**
```
filter @message like /session_lifecycle/
| parse @message '"action": "*"' as action
| parse @message '"new_status": "*"' as new_status
| stats count(*) as total by action, new_status
| sort total desc
```

---

## 4. Tips for Efficient Log Analysis

### Narrow the Time Range
Always set the tightest time window possible in Logs Insights. Queries scan all log data in the selected range — narrowing from "last 24h" to "last 1h" can cut query time significantly.

### Use `session_id` as Your Primary Correlation Key
Every log layer (middleware, LLM calls, pipeline stages, guardrails) propagates `session_id` via Python `contextvars`. Filter by `session_id` to reconstruct the full execution trace for a single user session — from initial HTTP request through every LLM call and pipeline stage to the final response.

### Use `request_id` for Individual Request Debugging
Each HTTP request gets a unique 8-character `request_id` assigned by the middleware. Use this to isolate logs for a single request when a session has many requests.

### Parse Before You Filter
CloudWatch Logs Insights queries are faster when you `filter` on raw `@message` first (string match), then `parse` the fields you need. Avoid parsing all messages and filtering on parsed fields when possible.

```
# Faster — filter first, then parse
filter @message like /llm_call/
| parse @message '"task_type": "*"' as task_type

# Slower — parse everything, then filter
| parse @message '"event": "*"' as event
| filter event = "llm_call"
```

### Export for Deep Analysis
For analysis beyond what Logs Insights supports (e.g., statistical modelling, cross-session aggregation):
1. **CloudWatch Logs Insights** — use `stats` and `bin()` for time-series aggregation directly in the console
2. **Export to S3** — use `aws logs create-export-task` to export log data to S3 for processing with Athena, pandas, or other tools
3. **Live tail** — use `aws logs tail /jobaid/backend --follow` from the CLI for real-time log streaming during debugging

### Set Up Metric Filters for Alerting
For critical events you want to alert on (beyond the existing CPU and instance health alarms), create CloudWatch Metric Filters:

```bash
# Example: create a metric for guardrail triggers
aws cloudwatch put-metric-filter \
  --log-group-name /jobaid/backend \
  --filter-name GuardrailTriggers \
  --filter-pattern '"guardrail_triggered"' \
  --metric-transformations \
    metricName=GuardrailTriggerCount,metricNamespace=JobAId,metricValue=1
```

Then create a CloudWatch Alarm on the metric to get notified (e.g., via SNS) when guardrail triggers exceed a threshold.

---

## 5. Log Schema Reference

### API Request Log (middleware)
```json
{
  "timestamp": "2026-03-15T10:30:00+00:00",
  "request_id": "ab12cd34",
  "method": "POST",
  "path": "/api/sessions/uuid/pipeline",
  "status": 200,
  "duration": 4.231,
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "query": "stage=parsing"
}
```

### LLM Call Log
```json
{
  "event": "llm_call",
  "timestamp": "2026-03-15T10:30:01+00:00",
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "model": "gpt-4o-mini",
  "task_type": "resume_parsing",
  "prompt_tokens": 1200,
  "completion_tokens": 450,
  "total_tokens": 1650,
  "latency_ms": 2100.5,
  "status": "success",
  "error": "..."
}
```

> **Note:** The `status` field (`"success"` or `"error"`) and `error` field are present when logged via the `logged_invoke()` helper. Calls logged directly via `LLMCallLogger.log_call()` omit these fields.

### LLM Session Summary
```json
{
  "event": "llm_session_summary",
  "timestamp": "2026-03-15T10:35:00+00:00",
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "total_calls": 8,
  "total_tokens": 12500,
  "total_latency_ms": 15200.3,
  "avg_latency_ms": 1900.0
}
```

### Pipeline Stage Log
```json
{
  "event": "pipeline_stage",
  "timestamp": "2026-03-15T10:30:05+00:00",
  "stage": "discovery",
  "status": "success",
  "latency_ms": 3200,
  "session_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

### Guardrail Trigger Log
```json
{
  "event": "guardrail_triggered",
  "timestamp": "2026-03-15T10:30:00+00:00",
  "guardrail": "prompt_injection",
  "stage": "resume_input",
  "detail": "matched pattern: ignore\\s+(all\\s+)?(previous|above|prior)..."
}
```

### Frontend Telemetry Log
```json
{
  "event": "frontend",
  "message": "HTTP error",
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "client_ts": "2026-03-15T10:30:00.000Z",
  "context": {
    "url": "/api/sessions/uuid/pipeline",
    "method": "POST",
    "status": 500,
    "duration_ms": 30100
  }
}
```

### Debug Trace Log
```json
{
  "event": "debug",
  "timestamp": "2026-03-15T10:30:00+00:00",
  "prefix": "ORCHESTRATOR",
  "message": "Routing to discovery stage"
}
```
