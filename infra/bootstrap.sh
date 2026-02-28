#!/bin/bash
# One-time setup: Create S3 bucket and DynamoDB table for Terraform remote state.
# Run this ONCE before the first `terraform init`.

set -euo pipefail

REGION="ap-southeast-1"
BUCKET="jobaid-terraform-state"
TABLE="jobaid-terraform-locks"

echo "Creating S3 bucket for Terraform state..."
aws s3api create-bucket \
  --bucket "$BUCKET" \
  --region "$REGION" \
  --create-bucket-configuration LocationConstraint="$REGION" \
  2>/dev/null || echo "Bucket already exists"

aws s3api put-bucket-versioning \
  --bucket "$BUCKET" \
  --versioning-configuration Status=Enabled

aws s3api put-bucket-encryption \
  --bucket "$BUCKET" \
  --server-side-encryption-configuration '{
    "Rules": [{"ApplyServerSideEncryptionByDefault": {"SSEAlgorithm": "AES256"}}]
  }'

echo "Creating DynamoDB table for state locking..."
aws dynamodb create-table \
  --table-name "$TABLE" \
  --attribute-definitions AttributeName=LockID,AttributeType=S \
  --key-schema AttributeName=LockID,KeyType=HASH \
  --billing-mode PAY_PER_REQUEST \
  --region "$REGION" \
  2>/dev/null || echo "Table already exists"

echo ""
echo "Done! You can now run:"
echo "  terraform init"
echo "  terraform plan"
echo "  terraform apply"
