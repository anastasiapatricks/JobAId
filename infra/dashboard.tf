resource "aws_cloudwatch_dashboard" "jobaid" {
  dashboard_name = "jobaid-dashboard"

  dashboard_body = jsonencode({
    widgets = [
      # ── Row 0: EC2 metrics ──────────────────────────────────────────
      {
        type   = "metric"
        x      = 0
        y      = 0
        width  = 12
        height = 6
        properties = {
          title   = "EC2 CPU Utilization"
          metrics = [["AWS/EC2", "CPUUtilization", "InstanceId", aws_instance.jobaid.id]]
          period  = 300
          stat    = "Average"
          region  = var.region
          view    = "timeSeries"
        }
      },
      {
        type   = "metric"
        x      = 12
        y      = 0
        width  = 12
        height = 6
        properties = {
          title = "Network In/Out"
          metrics = [
            ["AWS/EC2", "NetworkIn", "InstanceId", aws_instance.jobaid.id],
            ["AWS/EC2", "NetworkOut", "InstanceId", aws_instance.jobaid.id],
          ]
          period = 300
          stat   = "Sum"
          region = var.region
          view   = "timeSeries"
        }
      },

      # ── Row 6: Backend error logs ───────────────────────────────────
      {
        type   = "log"
        x      = 0
        y      = 6
        width  = 24
        height = 6
        properties = {
          title  = "Backend Error Logs"
          query  = "SOURCE '/jobaid/backend' | fields @timestamp, @message | filter @message like /ERROR|WARNING/ | sort @timestamp desc | limit 20"
          region = var.region
          view   = "table"
        }
      },

      # ── Row 12: LLM call tables ────────────────────────────────────
      {
        type   = "log"
        x      = 0
        y      = 12
        width  = 12
        height = 6
        properties = {
          title  = "LLM Call Latency by Agent"
          query  = "SOURCE '/jobaid/backend' | parse @message '\"task_type\": \"*\"' as task_type | parse @message '\"latency_ms\": *,' as latency_ms | parse @message '\"total_tokens\": *,' as total_tokens | filter @message like /llm_call/ | stats avg(latency_ms) as avg_latency, max(latency_ms) as max_latency, sum(total_tokens) as tokens, count(*) as calls by task_type"
          region = var.region
          view   = "table"
        }
      },
      {
        type   = "log"
        x      = 12
        y      = 12
        width  = 12
        height = 6
        properties = {
          title  = "Recent LLM Calls"
          query  = "SOURCE '/jobaid/backend' | parse @message '\"task_type\": \"*\"' as task_type | parse @message '\"latency_ms\": *,' as latency_ms | parse @message '\"total_tokens\": *,' as total_tokens | parse @message '\"model\": \"*\"' as model | parse @message '\"status\": \"*\"' as status | filter @message like /llm_call/ | display @timestamp, task_type, latency_ms, total_tokens, model, status | sort @timestamp desc | limit 20"
          region = var.region
          view   = "table"
        }
      },

      # ── Row 18: A1 API Request Throughput + A2 API Error Rate ──────
      {
        type   = "log"
        x      = 0
        y      = 18
        width  = 12
        height = 6
        properties = {
          title  = "API Request Throughput"
          query  = "SOURCE '/jobaid/backend' | filter @message like /\"method\"/ | parse @message '\"method\": \"*\"' as method | stats count(*) as requests by bin(5m)"
          region = var.region
          view   = "timeSeries"
        }
      },
      {
        type   = "log"
        x      = 12
        y      = 18
        width  = 12
        height = 6
        properties = {
          title  = "API Error Rate 4xx/5xx"
          query  = "SOURCE '/jobaid/backend' | filter @message like /\"status\"/ | parse @message '\"status\": *,' as status_code | parse @message '\"method\": \"*\"' as method | filter method in [\"POST\",\"GET\",\"PUT\",\"DELETE\",\"PATCH\"] | stats sum(status_code >= 400) as errors, count(*) as total by bin(5m)"
          region = var.region
          view   = "timeSeries"
        }
      },

      # ── Row 24: A3 API Latency Percentiles + A4 Slowest Endpoints ─
      {
        type   = "log"
        x      = 0
        y      = 24
        width  = 12
        height = 6
        properties = {
          title  = "API Latency Percentiles p50/p90/p99"
          query  = "SOURCE '/jobaid/backend' | filter @message like /\"duration\"/ | parse @message '\"duration\": *}' as duration_sec | parse @message '\"method\": \"*\"' as method | filter method in [\"POST\",\"GET\",\"PUT\",\"DELETE\",\"PATCH\"] | stats avg(duration_sec) as avg_s, pct(duration_sec, 50) as p50, pct(duration_sec, 90) as p90, pct(duration_sec, 99) as p99 by bin(5m)"
          region = var.region
          view   = "timeSeries"
        }
      },
      {
        type   = "log"
        x      = 12
        y      = 24
        width  = 12
        height = 6
        properties = {
          title  = "Slowest API Endpoints"
          query  = "SOURCE '/jobaid/backend' | filter @message like /\"duration\"/ | parse @message '\"method\": \"*\"' as method | parse @message '\"path\": \"*\"' as path | parse @message '\"duration\": *}' as duration_sec | filter method in [\"POST\",\"GET\",\"PUT\",\"DELETE\",\"PATCH\"] | stats avg(duration_sec) as avg_s, max(duration_sec) as max_s, count(*) as calls by method, path | sort avg_s desc | limit 10"
          region = var.region
          view   = "table"
        }
      },

      # ── Row 30: A5 LLM Token Usage + A6 LLM Token Cost by Task ────
      {
        type   = "log"
        x      = 0
        y      = 30
        width  = 12
        height = 6
        properties = {
          title  = "LLM Token Usage Over Time"
          query  = "SOURCE '/jobaid/backend' | filter @message like /llm_call/ | parse @message '\"prompt_tokens\": *,' as prompt_tokens | parse @message '\"completion_tokens\": *,' as completion_tokens | parse @message '\"total_tokens\": *,' as total_tokens | stats sum(prompt_tokens) as total_prompt, sum(completion_tokens) as total_completion, sum(total_tokens) as grand_total by bin(5m)"
          region = var.region
          view   = "timeSeries"
        }
      },
      {
        type   = "log"
        x      = 12
        y      = 30
        width  = 12
        height = 6
        properties = {
          title  = "LLM Token Cost by Task Type"
          query  = "SOURCE '/jobaid/backend' | filter @message like /llm_call/ | parse @message '\"task_type\": \"*\"' as task_type | parse @message '\"prompt_tokens\": *,' as prompt_tokens | parse @message '\"completion_tokens\": *,' as completion_tokens | parse @message '\"total_tokens\": *,' as total_tokens | stats sum(prompt_tokens) as prompt_tok, sum(completion_tokens) as completion_tok, sum(total_tokens) as total_tok, count(*) as calls by task_type | sort total_tok desc"
          region = var.region
          view   = "table"
        }
      },

      # ── Row 36: A7 LLM Call Errors + A8 LLM Session Summaries ─────
      {
        type   = "log"
        x      = 0
        y      = 36
        width  = 12
        height = 6
        properties = {
          title  = "LLM Call Errors"
          query  = "SOURCE '/jobaid/backend' | filter @message like /llm_call/ and @message like /\"error\"/ | parse @message '\"task_type\": \"*\"' as task_type | parse @message '\"error\": \"*\"' as error_msg | parse @message '\"model\": \"*\"' as model | parse @message '\"latency_ms\": *,' as latency_ms | display @timestamp, task_type, model, latency_ms, error_msg | sort @timestamp desc | limit 20"
          region = var.region
          view   = "table"
        }
      },
      {
        type   = "log"
        x      = 12
        y      = 36
        width  = 12
        height = 6
        properties = {
          title  = "LLM Session Summaries"
          query  = "SOURCE '/jobaid/backend' | filter @message like /llm_session_summary/ | parse @message '\"session_id\": \"*\"' as session_id | parse @message '\"total_calls\": *,' as total_calls | parse @message '\"total_tokens\": *,' as total_tokens | parse @message '\"total_latency_ms\": *,' as total_latency_ms | parse @message '\"avg_latency_ms\": *}' as avg_latency_ms | display @timestamp, session_id, total_calls, total_tokens, total_latency_ms, avg_latency_ms | sort @timestamp desc | limit 20"
          region = var.region
          view   = "table"
        }
      },

      # ── Row 42: A9 Recent API Errors Detail (full-width) ──────────
      {
        type   = "log"
        x      = 0
        y      = 42
        width  = 24
        height = 6
        properties = {
          title  = "Recent API Errors Detail"
          query  = "SOURCE '/jobaid/backend' | filter @message like /\"status\"/ | parse @message '\"method\": \"*\"' as method | parse @message '\"path\": \"*\"' as path | parse @message '\"status\": *,' as status_code | parse @message '\"duration\": *}' as duration_sec | parse @message '\"request_id\": \"*\"' as request_id | filter status_code >= 400 | display @timestamp, request_id, method, path, status_code, duration_sec | sort @timestamp desc | limit 20"
          region = var.region
          view   = "table"
        }
      },

      # ── Row 48: B1 Pipeline Stage Timing (table) + B2 Pipeline Stage Latency (timeSeries) ──
      {
        type   = "log"
        x      = 0
        y      = 48
        width  = 12
        height = 6
        properties = {
          title  = "Pipeline Stage Timing"
          query  = "SOURCE '/jobaid/backend' | filter @message like /pipeline_stage/ | parse @message '\"stage\": \"*\"' as stage | parse @message '\"status\": \"*\"' as status | parse @message '\"latency_ms\": *,' as latency_ms | stats avg(latency_ms) as avg_ms, max(latency_ms) as max_ms, sum(status = \"error\") as errors, count(*) as calls by stage | sort avg_ms desc"
          region = var.region
          view   = "table"
        }
      },
      {
        type   = "log"
        x      = 12
        y      = 48
        width  = 12
        height = 6
        properties = {
          title  = "Pipeline Stage Latency Over Time"
          query  = "SOURCE '/jobaid/backend' | filter @message like /pipeline_stage/ | parse @message '\"stage\": \"*\"' as stage | parse @message '\"latency_ms\": *,' as latency_ms | stats avg(latency_ms) as avg_ms by stage, bin(5m)"
          region = var.region
          view   = "timeSeries"
        }
      },

      # ── Row 54: B3 External API Health (table) + B4 External API Latency (timeSeries) ──
      {
        type   = "log"
        x      = 0
        y      = 54
        width  = 8
        height = 6
        properties = {
          title  = "External API Health"
          query  = "SOURCE '/jobaid/backend' | filter @message like /external_api_call/ | parse @message '\"service\": \"*\"' as service | parse @message '\"operation\": \"*\"' as operation | parse @message '\"status\": \"*\"' as status | parse @message '\"latency_ms\": *,' as latency_ms | stats avg(latency_ms) as avg_ms, max(latency_ms) as max_ms, sum(status = \"error\") as errors, count(*) as calls by service, operation"
          region = var.region
          view   = "table"
        }
      },
      {
        type   = "log"
        x      = 8
        y      = 54
        width  = 8
        height = 6
        properties = {
          title  = "External API Latency Over Time"
          query  = "SOURCE '/jobaid/backend' | filter @message like /external_api_call/ | parse @message '\"service\": \"*\"' as service | parse @message '\"latency_ms\": *,' as latency_ms | stats avg(latency_ms) as avg_ms by service, bin(5m)"
          region = var.region
          view   = "timeSeries"
        }
      },
      # B5: External API Result Counts
      {
        type   = "log"
        x      = 16
        y      = 54
        width  = 8
        height = 6
        properties = {
          title  = "External API Result Counts"
          query  = "SOURCE '/jobaid/backend' | filter @message like /external_api_call/ | parse @message '\"service\": \"*\"' as service | parse @message '\"operation\": \"*\"' as operation | parse @message '\"result_count\": *,' as result_count | parse @message '\"status\": \"*\"' as status | filter status = \"success\" | stats avg(result_count) as avg_results, sum(result_count) as total_results, count(*) as calls by service, operation"
          region = var.region
          view   = "table"
        }
      },

      # ── Row 60: B6 Session Activity (timeSeries) + B7 Session Funnel (table) ──
      {
        type   = "log"
        x      = 0
        y      = 60
        width  = 12
        height = 6
        properties = {
          title  = "Session Activity Over Time"
          query  = "SOURCE '/jobaid/backend' | filter @message like /session_lifecycle/ | parse @message '\"action\": \"*\"' as action | stats count(*) as events by action, bin(5m)"
          region = var.region
          view   = "timeSeries"
        }
      },
      {
        type   = "log"
        x      = 12
        y      = 60
        width  = 12
        height = 6
        properties = {
          title  = "Session Funnel"
          query  = "SOURCE '/jobaid/backend' | filter @message like /session_lifecycle/ | parse @message '\"action\": \"*\"' as action | parse @message '\"new_status\": \"*\"' as new_status | stats count(*) as total by action, new_status | sort total desc"
          region = var.region
          view   = "table"
        }
      },

      # ── Row 66: B8 Guardrail Triggers (full-width) ────────────────
      {
        type   = "log"
        x      = 0
        y      = 66
        width  = 24
        height = 6
        properties = {
          title  = "Guardrail Triggers"
          query  = "SOURCE '/jobaid/backend' | filter @message like /guardrail_triggered/ | parse @message '\"guardrail\": \"*\"' as guardrail | parse @message '\"stage\": \"*\"' as stage | parse @message '\"detail\": \"*\"' as detail | display @timestamp, guardrail, stage, detail | sort @timestamp desc | limit 30"
          region = var.region
          view   = "table"
        }
      },
    ]
  })
}
