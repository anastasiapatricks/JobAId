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
        width  = 24
        height = 6
        properties = {
          title  = "LLM Call Latency"
          query  = "SOURCE '/jobaid/backend' | fields @timestamp, @message | filter @message like /llm_call/ | sort @timestamp desc | limit 20"
          region = var.region
          view   = "table"
        }
      },
    ]
  })
}
