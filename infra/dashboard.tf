resource "aws_cloudwatch_dashboard" "jobaid" {
  dashboard_name = "jobaid-dashboard"

  dashboard_body = jsonencode({
    widgets = [
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
    ]
  })
}
