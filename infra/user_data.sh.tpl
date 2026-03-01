#!/bin/bash
set -euo pipefail

# Create swap file (2 GB) to compensate for limited RAM
fallocate -l 2G /swapfile
chmod 600 /swapfile
mkswap /swapfile
swapon /swapfile
echo '/swapfile swap swap defaults 0 0' >> /etc/fstab

# Install Docker
dnf install -y docker
systemctl enable docker
systemctl start docker
usermod -aG docker ec2-user

# Install Docker Compose plugin
mkdir -p /usr/local/lib/docker/cli-plugins
curl -SL "https://github.com/docker/compose/releases/latest/download/docker-compose-linux-x86_64" \
  -o /usr/local/lib/docker/cli-plugins/docker-compose
chmod +x /usr/local/lib/docker/cli-plugins/docker-compose

# Login to ECR
aws ecr get-login-password --region ${region} | \
  docker login --username AWS --password-stdin ${account_id}.dkr.ecr.${region}.amazonaws.com

# Write .env file
cat > /home/ec2-user/.env << 'ENVEOF'
OPENAI_API_KEY=${openai_api_key}
TAVILY_API_KEY=${tavily_api_key}
ADZUNA_APP_ID=${adzuna_app_id}
ADZUNA_API_KEY=${adzuna_api_key}
ENVEOF

chown ec2-user:ec2-user /home/ec2-user/.env
chmod 600 /home/ec2-user/.env

# Write docker-compose.prod.yml
cat > /home/ec2-user/docker-compose.prod.yml << 'COMPOSEEOF'
services:
  backend:
    image: ${ecr_backend_url}:latest
    env_file: .env
    healthcheck:
      test: ["CMD", "python", "-c", "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/health')"]
      interval: 30s
      timeout: 10s
      retries: 5
      start_period: 120s
    logging:
      driver: awslogs
      options:
        awslogs-region: ${region}
        awslogs-group: /jobaid/backend

  frontend:
    image: ${ecr_frontend_url}:latest
    ports:
      - "80:80"
    depends_on:
      backend:
        condition: service_healthy
    logging:
      driver: awslogs
      options:
        awslogs-region: ${region}
        awslogs-group: /jobaid/frontend
COMPOSEEOF

chown ec2-user:ec2-user /home/ec2-user/docker-compose.prod.yml

# Start services
cd /home/ec2-user
docker compose -f docker-compose.prod.yml up -d
