# Design Team File Manager

A FastAPI web application integrated with AWS S3 for a design team to upload, browse, download, and delete images and backup files. Infrastructure provisioned with Terraform and deployed on ECS Fargate.

## Stack

- **Backend:** FastAPI + uvicorn
- **Frontend:** Jinja2 + HTMX + Tailwind CSS (CDN)
- **Storage:** AWS S3 (no database)
- **Auth:** Session-based password gate (itsdangerous)
- **Infrastructure:** Terraform → VPC, ALB, ECS Fargate, S3, ECR
- **Testing:** pytest + moto (mocked S3) + httpx

## Project Structure

```
project1/
├── app/              # Python web application
│   ├── main.py       # FastAPI routes + auth middleware
│   ├── auth.py       # Password gate session tokens
│   ├── s3_client.py  # S3 CRUD operations
│   ├── templates/    # Jinja2 templates
│   ├── static/       # CSS
│   ├── Dockerfile
│   └── requirements.txt
├── infra/            # Terraform configuration
│   ├── main.tf       # Provider setup
│   ├── variables.tf  # Input variables
│   ├── outputs.tf    # ALB URL, bucket name, ECR URL
│   ├── vpc.tf        # Networking
│   ├── s3.tf         # S3 bucket + IAM policies
│   ├── ecr.tf        # ECR repository
│   └── ecs.tf        # ECS Fargate + ALB
├── tests/            # 22 tests (all passing)
│   ├── test_auth.py
│   ├── test_s3_client.py
│   └── test_routes.py
├── Makefile
└── docker-compose.yml
```

## Quick Start (Local Dev)

```bash
# Copy environment config
cp .env.example .env
# Edit .env with your AWS credentials and password

# Start the app with Docker Compose
docker compose up

# Or run locally
cd app
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Open http://localhost:8000 and sign in with the password from `.env`.

## Running Tests

```bash
cd app
pip install -r requirements.txt
pytest ../tests -v
```

Tests use moto to mock AWS S3 — no real AWS credentials needed.

## Deployment

```bash
# 1. Build and push Docker image to ECR
AWS_REGION=us-east-1 ECR_REPO=<ecr-repo-url> IMAGE_TAG=latest make up

# 2. Provision infrastructure
cd infra
terraform init
terraform apply -var="app_password=<your-password>"
```

For production, consider storing `APP_PASSWORD` in AWS SSM Parameter Store instead of passing it as a plain variable.

## Design

See [docs/superpowers/specs/2026-05-28-design-file-manager-design.md](docs/superpowers/specs/2026-05-28-design-file-manager-design.md) for the full design specification.
