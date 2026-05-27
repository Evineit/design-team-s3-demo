# Design Team File Manager — Design Spec

## Overview
A Python web application backed by AWS S3 for a design team to upload, browse, download, and delete images and backup files. Infrastructure provisioned with Terraform, deployed on ECS Fargate.

## Stack
- **Backend:** FastAPI (Python) + uvicorn
- **Frontend:** Jinja2 templates + HTMX + Tailwind CSS (CDN)
- **Storage:** AWS S3 (no database)
- **Auth:** Simple session-based password gate (cookie signed with `itsdangerous`)
- **Infra:** Terraform → VPC, ALB, ECS Fargate, S3, ECR
- **Testing:** pytest + moto (mock S3) + FastAPI TestClient

## Application Structure
```
project1/
├── app/
│   ├── main.py
│   ├── auth.py
│   ├── s3_client.py
│   ├── templates/
│   │   ├── base.html
│   │   ├── index.html
│   │   └── login.html
│   ├── static/
│   │   └── style.css
│   ├── requirements.txt
│   └── Dockerfile
├── infra/
│   ├── main.tf
│   ├── vpc.tf
│   ├── s3.tf
│   ├── ecr.tf
│   ├── ecs.tf
│   ├── outputs.tf
│   └── variables.tf
├── Makefile
├── docker-compose.yml
├── tests/
│   ├── test_s3_client.py
│   ├── test_auth.py
│   └── test_routes.py
└── docs/superpowers/specs/
```

## Application Design

### Auth (`auth.py`)
- Single password from env var `APP_PASSWORD`
- Session cookie signed with `itsdangerous`
- Middleware: check cookie on all routes except `/login`
- `/login` GET → form, POST → validate + set cookie, redirect to `/`
- Logout clears cookie

### S3 Client (`s3_client.py`)
- `list_files()` → returns key, size, last_modified for objects in bucket
- `upload_file(file, key)` → streams upload from FastAPI UploadFile to S3
- `download_file(key)` → streams from S3, returns StreamingResponse
- `delete_file(key)` → deletes object
- Paths: `designs/` prefix for design files, `backups/` for backups
- Content-type inferred from file extension

### Routes (`main.py`)
- `GET /` → file listing (image thumbnails for images, icons for other files)
- `POST /upload` → accept multipart upload, stream to S3, redirect
- `GET /download/{key}` → stream download from S3
- `POST /delete/{key}` → delete from S3, redirect
- `GET /login`, `POST /login`, `GET /logout` → auth
- HTMX for file operations to avoid full page reloads

## Infrastructure Design

### VPC (`vpc.tf`)
- 2 AZs: 2 public + 2 private subnets
- ALB in public subnets, ECS tasks in private
- NAT Gateway for outbound ECS→S3 access
- Security groups: ALB allows HTTP from 0.0.0.0/0; ECS allows inbound from ALB only

### S3 (`s3.tf`)
- Private bucket: `design-file-manager-{suffix}`
- Versioning enabled
- SSE-S3 encryption at rest
- Lifecycle: abort incomplete multipart uploads after 7 days
- Bucket policy: deny non-SSL requests
- IAM policy: ECS task role gets read/write on this bucket

### ECR (`ecr.tf`)
- Repository with image scanning on push
- Lifecycle: keep last 5 images

### ECS Fargate (`ecs.tf`)
- Cluster: Fargate only
- Task: 0.5 vCPU, 1 GB memory, port 8000
- Env vars: `S3_BUCKET`, `AWS_REGION`, `APP_PASSWORD` (from SSM or plain env var)
- Task IAM role with S3 policy attached
- Service: 1 task, behind ALB
- ALB: HTTP listener, health check on `/`

### Variables
- `environment` (default: `dev`)
- `aws_region` (default: `us-east-1`)
- `app_password`
- `image_tag` (default: `latest`)

### Outputs
- `alb_url`, `s3_bucket_name`, `ecr_repository_url`

## Deployment
- `Makefile` with: `make build`, `make push`, `make deploy`, `make up`
- Manual flow: build → push to ECR → terraform apply
- `docker-compose.yml` for local dev (localstack/MinIO or real AWS creds, `.env` file)

## Error Handling
- Upload too large → 413 with message (default max 50MB)
- S3 errors → logged, shown as error banner in UI
- File not found → 404 page
- Auth failure → "wrong password" message on login form
- Duplicate filename → overwrite (versioning protects old version)

## Testing
- `moto` for mocking S3 in unit tests
- FastAPI `TestClient` for route integration tests
- Test files: `test_s3_client.py`, `test_auth.py`, `test_routes.py`
