terraform {
  required_version = ">= 1.5"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }

  backend "s3" {
    bucket         = "jobaid-terraform-state"
    key            = "terraform.tfstate"
    region         = "ap-southeast-1"
    dynamodb_table = "jobaid-terraform-locks"
    encrypt        = true
  }
}

provider "aws" {
  region = var.region
}

data "aws_caller_identity" "current" {}

# --- ECR Repositories ---

resource "aws_ecr_repository" "backend" {
  name                 = "jobaid-backend"
  image_tag_mutability = "MUTABLE"
  force_delete         = true

  image_scanning_configuration {
    scan_on_push = true
  }
}

resource "aws_ecr_repository" "frontend" {
  name                 = "jobaid-frontend"
  image_tag_mutability = "MUTABLE"
  force_delete         = true

  image_scanning_configuration {
    scan_on_push = true
  }
}

# --- IAM Role for EC2 (ECR pull + CloudWatch Logs) ---

resource "aws_iam_role" "ec2_role" {
  name = "jobaid-ec2-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = {
        Service = "ec2.amazonaws.com"
      }
    }]
  })
}

resource "aws_iam_role_policy" "ec2_ecr_policy" {
  name = "jobaid-ecr-access"
  role = aws_iam_role.ec2_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "ecr:GetAuthorizationToken",
          "ecr:BatchGetImage",
          "ecr:GetDownloadUrlForLayer",
          "ecr:BatchCheckLayerAvailability",
        ]
        Resource = "*"
      },
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents",
          "logs:DescribeLogStreams",
        ]
        Resource = "arn:aws:logs:${var.region}:${data.aws_caller_identity.current.account_id}:*"
      },
    ]
  })
}

resource "aws_iam_instance_profile" "ec2_profile" {
  name = "jobaid-ec2-profile"
  role = aws_iam_role.ec2_role.name
}

# --- CloudWatch Log Groups ---

resource "aws_cloudwatch_log_group" "backend" {
  name              = "/jobaid/backend"
  retention_in_days = 7
}

resource "aws_cloudwatch_log_group" "frontend" {
  name              = "/jobaid/frontend"
  retention_in_days = 7
}

# --- Security Group ---

resource "aws_security_group" "jobaid" {
  name        = "jobaid-sg"
  description = "Allow HTTP and SSH access"

  ingress {
    description = "HTTP"
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    description = "SSH"
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = [var.allowed_ssh_cidr]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

# --- EC2 Instance ---

data "aws_ami" "amazon_linux" {
  most_recent = true
  owners      = ["amazon"]

  filter {
    name   = "name"
    values = ["al2023-ami-*-x86_64"]
  }

  filter {
    name   = "virtualization-type"
    values = ["hvm"]
  }
}

resource "aws_instance" "jobaid" {
  ami                    = data.aws_ami.amazon_linux.id
  instance_type          = var.instance_type
  key_name               = var.key_name
  vpc_security_group_ids = [aws_security_group.jobaid.id]
  iam_instance_profile   = aws_iam_instance_profile.ec2_profile.name

  associate_public_ip_address = true

  root_block_device {
    volume_size = 8
    volume_type = "gp3"
  }

  user_data = base64encode(templatefile("${path.module}/user_data.sh.tpl", {
    region           = var.region
    account_id       = data.aws_caller_identity.current.account_id
    ecr_backend_url  = aws_ecr_repository.backend.repository_url
    ecr_frontend_url = aws_ecr_repository.frontend.repository_url
    openai_api_key   = var.openai_api_key
    tavily_api_key   = var.tavily_api_key
    adzuna_app_id    = var.adzuna_app_id
    adzuna_api_key   = var.adzuna_api_key
  }))

  tags = {
    Name    = "jobaid-server"
    Project = "JobAId"
  }
}

# --- CloudWatch Alarms ---

resource "aws_cloudwatch_metric_alarm" "instance_status" {
  alarm_name          = "jobaid-instance-status"
  comparison_operator = "GreaterThanOrEqualToThreshold"
  evaluation_periods  = 2
  metric_name         = "StatusCheckFailed"
  namespace           = "AWS/EC2"
  period              = 60
  statistic           = "Maximum"
  threshold           = 1
  alarm_description   = "EC2 instance status check failed"

  dimensions = {
    InstanceId = aws_instance.jobaid.id
  }

  alarm_actions = ["arn:aws:automate:${var.region}:ec2:recover"]
}

resource "aws_cloudwatch_metric_alarm" "high_cpu" {
  alarm_name          = "jobaid-high-cpu"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 5
  metric_name         = "CPUUtilization"
  namespace           = "AWS/EC2"
  period              = 60
  statistic           = "Average"
  threshold           = 80
  alarm_description   = "CPU utilization above 80% for 5 minutes"

  dimensions = {
    InstanceId = aws_instance.jobaid.id
  }
}
