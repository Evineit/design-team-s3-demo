# Design Team File Manager — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a FastAPI web app integrated with AWS S3 for a design team to upload, browse, download, and delete images and backup files, with infrastructure provisioned via Terraform.

**Architecture:** FastAPI proxy pattern — files upload through the app to S3 (not presigned URLs). Server-rendered HTML with HTMX. Single password gate auth. No database (S3-only metadata). ECS Fargate + ALB deployment.

**Tech Stack:** FastAPI, Jinja2, HTMX, Tailwind CSS (CDN), boto3, itsdangerous, pytest + moto, Terraform, ECS Fargate, ECR, S3

---

## File Structure

```
project1/
├── app/
│   ├── __init__.py
│   ├── main.py             # FastAPI app, routes, middleware
│   ├── auth.py             # Password gate: create/verify session
│   ├── s3_client.py        # CRUD operations on S3 bucket
│   ├── templates/
│   │   ├── base.html       # Layout with Tailwind + HTMX
│   │   ├── index.html      # File list + upload form
│   │   └── login.html      # Password form
│   ├── static/
│   │   └── style.css       # Minimal custom styles
│   ├── requirements.txt
│   └── Dockerfile
├── infra/
│   ├── main.tf             # Provider config
│   ├── variables.tf        # Input variables
│   ├── outputs.tf          # Outputs (ALB URL, bucket name, ECR URL)
│   ├── vpc.tf              # VPC, subnets, SG, NAT
│   ├── s3.tf               # Bucket + IAM policy
│   ├── ecr.tf              # ECR repository
│   └── ecs.tf              # ECS cluster + task definition + service + ALB
├── tests/
│   ├── __init__.py
│   ├── conftest.py         # pytest fixtures (moto, test client, etc.)
│   ├── test_auth.py        # Auth module tests
│   ├── test_s3_client.py   # S3 client tests with moto
│   └── test_routes.py      # Route integration tests
├── Makefile
├── docker-compose.yml
└── docs/superpowers/
    ├── specs/2026-05-28-design-file-manager-design.md
    └── plans/2026-05-28-design-file-manager-implementation.md
```

**Responsibility per file:**
- `app/auth.py` — session token creation and verification, no Flask/FastAPI imports (pure logic, testable)
- `app/s3_client.py` — all boto3 S3 operations, pure functions from environment config
- `app/main.py` — FastAPI app, route definitions, auth middleware, template context
- `infra/*.tf` — each Terraform file owns one AWS resource group, flat structure for readability
- `tests/conftest.py` — shared fixtures for moto mock S3, test FastAPI client, test auth tokens

---

### Task 1: Project Scaffolding

**Files:**
- Create: `app/__init__.py`
- Create: `tests/__init__.py`
- Create: `app/requirements.txt`
- Create: `app/Dockerfile`
- Create: `Makefile`
- Create: `docker-compose.yml`

- [ ] **Step 1: Create `app/__init__.py`**

Empty file.

- [ ] **Step 2: Create `tests/__init__.py`**

Empty file.

- [ ] **Step 3: Create `app/requirements.txt`**

```
fastapi==0.115.6
uvicorn[standard]==0.34.0
jinja2==3.1.5
boto3==1.36.16
python-multipart==0.0.20
itsdangerous==2.2.0
pytest==8.3.4
pytest-env==1.1.5
moto[s3]==5.0.28
httpx==0.28.1
```

- [ ] **Step 4: Create `app/Dockerfile`**

```dockerfile
FROM python:3.12-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

- [ ] **Step 5: Create `Makefile`**

```makefile
.PHONY: build push deploy up test

build:
	docker build -t design-file-manager app/

push:
	aws ecr get-login-password --region $(AWS_REGION) | docker login --username AWS --password-stdin $(ECR_REPO)
	docker tag design-file-manager $(ECR_REPO):$(IMAGE_TAG)
	docker push $(ECR_REPO):$(IMAGE_TAG)

deploy:
	cd infra && terraform apply -auto-approve

up: build push deploy

test:
	cd app && pip install -r requirements.txt && pytest ../tests -v
```

- [ ] **Step 6: Create `docker-compose.yml`**

```yaml
version: "3.9"
services:
  app:
    build: ./app
    ports:
      - "8000:8000"
    environment:
      - S3_BUCKET=${S3_BUCKET:-design-file-manager-local}
      - AWS_REGION=${AWS_REGION:-us-east-1}
      - APP_PASSWORD=${APP_PASSWORD:-secret123}
      - AWS_ACCESS_KEY_ID=${AWS_ACCESS_KEY_ID}
      - AWS_SECRET_ACCESS_KEY=${AWS_SECRET_ACCESS_KEY}
    volumes:
      - ./app:/app
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

- [ ] **Step 7: Commit**

```bash
git add app/__init__.py tests/__init__.py app/requirements.txt app/Dockerfile Makefile docker-compose.yml
git commit -m "chore: scaffold project structure"
```

---

### Task 2: Auth Module (TDD)

**Files:**
- Create: `tests/conftest.py`
- Create: `tests/test_auth.py`
- Create: `app/auth.py`

- [ ] **Step 1: Create `tests/conftest.py` with shared fixtures**

```python
import pytest
from itsdangerous import URLSafeTimedSerializer


@pytest.fixture
def auth_secret():
    return "test-secret-key"


@pytest.fixture
def serializer(auth_secret):
    return URLSafeTimedSerializer(auth_secret, salt="auth")
```

- [ ] **Step 2: Write failing tests in `tests/test_auth.py`**

```python
import pytest
from app.auth import create_session_token, verify_session_token


class TestCreateSessionToken:
    def test_returns_a_string(self, auth_secret):
        token = create_session_token("correct", auth_secret)
        assert isinstance(token, str)
        assert len(token) > 0

    def test_different_tokens_for_different_passwords(self, auth_secret):
        t1 = create_session_token("pass1", auth_secret)
        t2 = create_session_token("pass2", auth_secret)
        assert t1 != t2


class TestVerifySessionToken:
    def test_returns_true_for_valid_token(self, auth_secret):
        token = create_session_token("correct", auth_secret)
        assert verify_session_token(token, "correct", auth_secret) is True

    def test_returns_false_for_wrong_password(self, auth_secret):
        token = create_session_token("correct", auth_secret)
        assert verify_session_token(token, "wrong", auth_secret) is False

    def test_returns_false_for_garbage_token(self, auth_secret):
        assert verify_session_token("garbage", "correct", auth_secret) is False

    def test_returns_false_for_expired_token(self, auth_secret):
        import time
        token = create_session_token("correct", auth_secret, max_age=1)
        time.sleep(1.5)
        assert verify_session_token(token, "correct", auth_secret) is False
```

- [ ] **Step 3: Run tests to confirm they fail**

Run: `cd app; pip install -r requirements.txt > $null 2>&1; python -m pytest ../tests/test_auth.py -v`
Expected: ImportError — no module named `app.auth`

- [ ] **Step 4: Write minimal `app/auth.py`**

```python
from itsdangerous import URLSafeTimedSerializer


def _make_serializer(secret):
    return URLSafeTimedSerializer(secret, salt="auth")


def create_session_token(password, secret, max_age=86400):
    serializer = _make_serializer(secret)
    return serializer.dumps({"p": password})


def verify_session_token(token, expected_password, secret):
    try:
        serializer = _make_serializer(secret)
        data = serializer.loads(token, max_age=86400)
        return data.get("p") == expected_password
    except Exception:
        return False
```

- [ ] **Step 5: Run tests to confirm they pass**

Run: `cd app; python -m pytest ../tests/test_auth.py -v`
Expected: All 6 tests PASS

- [ ] **Step 6: Commit**

```bash
git add tests/conftest.py tests/test_auth.py app/auth.py
git commit -m "feat: add password gate auth module"
```

---

### Task 3: S3 Client Module (TDD)

**Files:**
- Create: `tests/test_s3_client.py`
- Create: `app/s3_client.py`

- [ ] **Step 1: Add moto fixtures to `tests/conftest.py`**

Edit `tests/conftest.py` — replace entire content with:

```python
import os
import pytest
from itsdangerous import URLSafeTimedSerializer
import boto3
from moto import mock_aws


@pytest.fixture
def auth_secret():
    return "test-secret-key"


@pytest.fixture
def serializer(auth_secret):
    return URLSafeTimedSerializer(auth_secret, salt="auth")


@pytest.fixture
def aws_credentials():
    os.environ["AWS_ACCESS_KEY_ID"] = "testing"
    os.environ["AWS_SECRET_ACCESS_KEY"] = "testing"
    os.environ["AWS_SECURITY_TOKEN"] = "testing"
    os.environ["AWS_SESSION_TOKEN"] = "testing"
    os.environ["AWS_DEFAULT_REGION"] = "us-east-1"


@pytest.fixture
def s3_mock(aws_credentials):
    with mock_aws():
        yield boto3.client("s3", region_name="us-east-1")


@pytest.fixture
def bucket_name():
    return "test-design-bucket"


@pytest.fixture
def s3_bucket(s3_mock, bucket_name):
    s3_mock.create_bucket(Bucket=bucket_name)
    return s3_mock
```

- [ ] **Step 2: Write failing tests in `tests/test_s3_client.py`**

```python
import io
import pytest
from app.s3_client import list_files, upload_file, download_file, delete_file


class TestListFiles:
    def test_returns_empty_list_for_empty_bucket(self, s3_bucket, bucket_name):
        files = list_files(bucket_name)
        assert files == []

    def test_lists_single_file(self, s3_bucket, bucket_name):
        s3_bucket.put_object(Bucket=bucket_name, Key="designs/test.png", Body=b"data")
        files = list_files(bucket_name)
        assert len(files) == 1
        assert files[0]["key"] == "designs/test.png"

    def test_lists_multiple_files(self, s3_bucket, bucket_name):
        s3_bucket.put_object(Bucket=bucket_name, Key="designs/a.png", Body=b"1")
        s3_bucket.put_object(Bucket=bucket_name, Key="backups/b.zip", Body=b"2")
        files = list_files(bucket_name)
        assert len(files) == 2

    def test_returns_keys_with_size_and_last_modified(self, s3_bucket, bucket_name):
        s3_bucket.put_object(Bucket=bucket_name, Key="designs/test.png", Body=b"hello")
        files = list_files(bucket_name)
        f = files[0]
        assert "key" in f
        assert "size" in f
        assert "last_modified" in f
        assert f["size"] == 5


class TestUploadFile:
    def test_uploads_file_to_s3(self, s3_bucket, bucket_name):
        file = io.BytesIO(b"image data")
        upload_file(file, "designs/logo.png", bucket_name)
        obj = s3_bucket.get_object(Bucket=bucket_name, Key="designs/logo.png")
        assert obj["Body"].read() == b"image data"

    def test_overwrites_existing_key(self, s3_bucket, bucket_name):
        s3_bucket.put_object(Bucket=bucket_name, Key="designs/logo.png", Body=b"old")
        file = io.BytesIO(b"new data")
        upload_file(file, "designs/logo.png", bucket_name)
        obj = s3_bucket.get_object(Bucket=bucket_name, Key="designs/logo.png")
        assert obj["Body"].read() == b"new data"


class TestDownloadFile:
    def test_downloads_existing_file(self, s3_bucket, bucket_name):
        s3_bucket.put_object(Bucket=bucket_name, Key="designs/logo.png", Body=b"hello")
        data = download_file("designs/logo.png", bucket_name)
        assert data.read() == b"hello"

    def test_raises_on_missing_file(self, s3_bucket, bucket_name):
        with pytest.raises(Exception):
            download_file("designs/missing.png", bucket_name)


class TestDeleteFile:
    def test_deletes_existing_file(self, s3_bucket, bucket_name):
        s3_bucket.put_object(Bucket=bucket_name, Key="designs/logo.png", Body=b"x")
        delete_file("designs/logo.png", bucket_name)
        objs = s3_bucket.list_objects_v2(Bucket=bucket_name)
        assert "Contents" not in objs or len(objs["Contents"]) == 0

    def test_succeeds_on_missing_file(self, s3_bucket, bucket_name):
        delete_file("designs/missing.png", bucket_name)
```

- [ ] **Step 3: Run tests to confirm they fail**

Run: `cd app; python -m pytest ../tests/test_s3_client.py -v`
Expected: ImportError — no module named `app.s3_client`

- [ ] **Step 4: Write minimal `app/s3_client.py`**

```python
import io
import boto3


def _client():
    return boto3.client("s3")


def list_files(bucket_name):
    client = _client()
    response = client.list_objects_v2(Bucket=bucket_name)
    contents = response.get("Contents", [])
    return [
        {
            "key": obj["Key"],
            "size": obj["Size"],
            "last_modified": obj["LastModified"],
        }
        for obj in contents
    ]


def upload_file(file, key, bucket_name):
    client = _client()
    client.upload_fileobj(file, bucket_name, key)


def download_file(key, bucket_name):
    client = _client()
    buf = io.BytesIO()
    client.download_fileobj(bucket_name, key, buf)
    buf.seek(0)
    return buf


def delete_file(key, bucket_name):
    client = _client()
    client.delete_object(Bucket=bucket_name, Key=key)
```

- [ ] **Step 5: Run tests to confirm they pass**

Run: `cd app; python -m pytest ../tests/test_s3_client.py -v`
Expected: All tests PASS

- [ ] **Step 6: Commit**

```bash
git add tests/conftest.py tests/test_s3_client.py app/s3_client.py
git commit -m "feat: add S3 client module with CRUD operations"
```

---

### Task 4: FastAPI App + Routes (TDD)

**Files:**
- Create: `tests/test_routes.py`
- Create: `app/main.py`

- [ ] **Step 1: Write failing tests in `tests/test_routes.py`**

```python
import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app


@pytest.fixture
def test_client(s3_bucket, bucket_name, monkeypatch):
    monkeypatch.setenv("S3_BUCKET", bucket_name)
    monkeypatch.setenv("APP_PASSWORD", "testpass")
    return app


@pytest.mark.anyio
async def test_login_page_returns_form(test_client):
    transport = ASGITransport(app=test_client)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/login")
    assert resp.status_code == 200
    assert "password" in resp.text.lower()


@pytest.mark.anyio
async def test_login_with_correct_password_redirects(test_client):
    transport = ASGITransport(app=test_client)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post("/login", data={"password": "testpass"})
    assert resp.status_code == 200
    assert len(client.cookies) > 0


@pytest.mark.anyio
async def test_login_with_wrong_password_shows_error(test_client):
    transport = ASGITransport(app=test_client)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post("/login", data={"password": "wrong"})
    assert resp.status_code == 200
    assert "incorrect" in resp.text.lower() or "wrong" in resp.text.lower()


@pytest.mark.anyio
async def test_index_redirects_to_login_when_unauthenticated(test_client):
    transport = ASGITransport(app=test_client)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/", follow_redirects=False)
    assert resp.status_code == 303 or resp.status_code == 302


@pytest.mark.anyio
async def test_index_shows_files_when_authenticated(test_client, s3_bucket, bucket_name):
    s3_bucket.put_object(Bucket=bucket_name, Key="designs/logo.png", Body=b"img")
    transport = ASGITransport(app=test_client)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        await client.post("/login", data={"password": "testpass"})
        resp = await client.get("/")
    assert resp.status_code == 200
    assert "logo.png" in resp.text


@pytest.mark.anyio
async def test_upload_endpoint_stores_file(test_client, s3_bucket, bucket_name):
    transport = ASGITransport(app=test_client)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        await client.post("/login", data={"password": "testpass"})
        resp = await client.post(
            "/upload",
            data={"file_type": "designs"},
            files={"file": ("photo.png", b"imagebytes", "image/png")},
        )
    assert resp.status_code == 200
    objs = s3_bucket.list_objects_v2(Bucket=bucket_name)
    keys = [o["Key"] for o in objs.get("Contents", [])]
    assert any("photo.png" in k for k in keys)
```

- [ ] **Step 2: Run tests to confirm they fail**

Run: `cd app; python -m pytest ../tests/test_routes.py -v`
Expected: ImportError — no module named `app.main`

- [ ] **Step 3: Write minimal `app/main.py`**

```python
import os
import mimetypes
from pathlib import PurePosixPath

from fastapi import FastAPI, Request, Form, UploadFile, File, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware

from .auth import create_session_token, verify_session_token

app = FastAPI()

templates = Jinja2Templates(directory=os.path.join(os.path.dirname(__file__), "templates"))
app.mount("/static", StaticFiles(directory=os.path.join(os.path.dirname(__file__), "static")), name="static")

S3_BUCKET = os.environ.get("S3_BUCKET", "design-file-manager")
APP_PASSWORD = os.environ.get("APP_PASSWORD", "admin")
SESSION_COOKIE = "session"


class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        public_paths = {"/login", "/static"}
        if request.url.path in public_paths or request.url.path.startswith("/static/"):
            return await call_next(request)
        token = request.cookies.get(SESSION_COOKIE)
        secret = APP_PASSWORD
        if not token or not verify_session_token(token, APP_PASSWORD, secret):
            if request.url.path == "/login":
                return await call_next(request)
            return RedirectResponse(url="/login", status_code=303)
        return await call_next(request)

app.add_middleware(AuthMiddleware)


@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request, error: str = ""):
    return templates.TemplateResponse("login.html", {"request": request, "error": error})


@app.post("/login")
async def login_post(request: Request, password: str = Form(...)):
    if password != APP_PASSWORD:
        return templates.TemplateResponse(
            "login.html", {"request": request, "error": "Incorrect password"}, status_code=200
        )
    token = create_session_token(password, APP_PASSWORD)
    resp = RedirectResponse(url="/", status_code=303)
    resp.set_cookie(key=SESSION_COOKIE, value=token, max_age=86400, httponly=True)
    return resp


@app.get("/logout")
async def logout():
    resp = RedirectResponse(url="/login", status_code=303)
    resp.delete_cookie(SESSION_COOKIE)
    return resp


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    from .s3_client import list_files

    files = list_files(S3_BUCKET)
    return templates.TemplateResponse("index.html", {"request": request, "files": files})


@app.post("/upload")
async def upload(file: UploadFile = File(...), file_type: str = Form("designs")):
    from .s3_client import upload_file

    contents = await file.read()
    import io
    buf = io.BytesIO(contents)
    key = f"{file_type}/{file.filename}"
    upload_file(buf, key, S3_BUCKET)
    return RedirectResponse(url="/", status_code=303)


@app.get("/download/{key:path}")
async def download(key: str):
    from .s3_client import download_file

    try:
        buf = download_file(key, S3_BUCKET)
        media_type, _ = mimetypes.guess_type(key)
        return StreamingResponse(
            buf,
            media_type=media_type or "application/octet-stream",
            headers={"Content-Disposition": f'attachment; filename="{PurePosixPath(key).name}"'},
        )
    except Exception:
        raise HTTPException(status_code=404, detail="File not found")


@app.post("/delete/{key:path}")
async def delete(key: str):
    from .s3_client import delete_file

    delete_file(key, S3_BUCKET)
    return RedirectResponse(url="/", status_code=303)
```

- [ ] **Step 4: Install httpx asyncio support and run tests**

Run: `cd app; pip install anyio > $null 2>&1; python -m pytest ../tests/test_routes.py -v`
Expected: All 7 tests PASS

- [ ] **Step 5: Commit**

```bash
git add tests/test_routes.py app/main.py
git commit -m "feat: add FastAPI app with routes and auth middleware"
```

---

### Task 5: Templates

**Files:**
- Create: `app/templates/base.html`
- Create: `app/templates/login.html`
- Create: `app/templates/index.html`

- [ ] **Step 1: Create `app/templates/base.html`**

```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Design File Manager</title>
    <script src="https://unpkg.com/htmx.org@2.0.4"></script>
    <script src="https://cdn.tailwindcss.com"></script>
    <link rel="stylesheet" href="/static/style.css">
</head>
<body class="bg-gray-50 min-h-screen">
    <nav class="bg-white shadow-sm border-b border-gray-200">
        <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div class="flex justify-between h-14 items-center">
                <a href="/" class="text-lg font-semibold text-gray-800">Design File Manager</a>
                <a href="/logout" class="text-sm text-gray-500 hover:text-gray-700">Logout</a>
            </div>
        </div>
    </nav>
    <main class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
        {% block content %}{% endblock %}
    </main>
</body>
</html>
```

- [ ] **Step 2: Create `app/templates/login.html`**

```html
{% extends "base.html" %}
{% block content %}
<div class="flex items-center justify-center min-h-[70vh]">
    <div class="bg-white p-8 rounded-lg shadow-md w-full max-w-sm">
        <h1 class="text-2xl font-semibold mb-6 text-center">Sign In</h1>
        {% if error %}
        <div class="mb-4 p-3 bg-red-50 border border-red-200 text-red-700 text-sm rounded">
            {{ error }}
        </div>
        {% endif %}
        <form method="post" action="/login">
            <label class="block text-sm font-medium text-gray-700 mb-1">Password</label>
            <input type="password" name="password" required
                   class="w-full border border-gray-300 rounded px-3 py-2 mb-4 focus:outline-none focus:ring-2 focus:ring-blue-400">
            <button type="submit"
                    class="w-full bg-blue-600 text-white py-2 rounded hover:bg-blue-700 transition">
                Sign In
            </button>
        </form>
    </div>
</div>
{% endblock %}
```

- [ ] **Step 3: Create `app/templates/index.html`**

```html
{% extends "base.html" %}
{% block content %}
<div class="mb-6 bg-white rounded-lg shadow-sm border border-gray-200 p-6">
    <h2 class="text-lg font-semibold mb-3">Upload File</h2>
    <form hx-post="/upload" hx-target="body" hx-indicator="#spinner"
          enctype="multipart/form-data" class="flex flex-wrap items-end gap-3">
        <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">Type</label>
            <select name="file_type" class="border border-gray-300 rounded px-3 py-2 text-sm">
                <option value="designs">Design</option>
                <option value="backups">Backup</option>
            </select>
        </div>
        <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">File</label>
            <input type="file" name="file" required
                   class="block text-sm text-gray-500 file:mr-3 file:py-1.5 file:px-3 file:rounded file:border-0 file:text-sm file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100">
        </div>
        <button type="submit"
                class="bg-blue-600 text-white px-4 py-2 rounded text-sm hover:bg-blue-700 transition">
            Upload
        </button>
    </form>
    <div id="spinner" class="htmx-indicator mt-2 text-sm text-gray-500">Uploading...</div>
</div>

<div class="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
    {% for file in files %}
    <div class="bg-white rounded-lg shadow-sm border border-gray-200 p-3 flex flex-col">
        <div class="text-sm font-medium text-gray-800 truncate" title="{{ file.key }}">
            {{ file.key.split('/', 1)[1] if '/' in file.key else file.key }}
        </div>
        <div class="text-xs text-gray-400 mt-1">
            {{ (file.size / 1024)|round(1) }} KB &middot;
            {{ file.last_modified.strftime('%Y-%m-%d %H:%M') }}
        </div>
        <div class="flex justify-between items-center mt-3 pt-2 border-t border-gray-100">
            <span class="text-xs bg-gray-100 text-gray-600 px-2 py-0.5 rounded">
                {{ file.key.split('/')[0] }}
            </span>
            <div class="flex gap-2">
                <a href="/download/{{ file.key }}"
                   class="text-blue-600 hover:text-blue-800 text-sm">Download</a>
                <form hx-post="/delete/{{ file.key }}" hx-target="body"
                      onsubmit="return confirm('Delete this file?')">
                    <button type="submit" class="text-red-500 hover:text-red-700 text-sm">Delete</button>
                </form>
            </div>
        </div>
    </div>
    {% else %}
    <div class="col-span-full text-center py-12 text-gray-400">
        No files uploaded yet. Upload your first file above.
    </div>
    {% endfor %}
</div>
{% endblock %}
```

- [ ] **Step 4: Commit**

```bash
git add app/templates/base.html app/templates/login.html app/templates/index.html
git commit -m "feat: add Jinja2 templates with HTMX and Tailwind"
```

---

### Task 6: Static CSS

**Files:**
- Create: `app/static/style.css`

- [ ] **Step 1: Create `app/static/style.css`**

```css
.htmx-indicator {
    display: none;
}
.htmx-request .htmx-indicator {
    display: inline;
}
.htmx-request.htmx-indicator {
    display: inline;
}
```

- [ ] **Step 2: Commit**

```bash
git add app/static/style.css
git commit -m "feat: add minimal static styles for HTMX loading indicator"
```

---

### Task 7: Terraform — Base + Variables + Outputs

**Files:**
- Create: `infra/main.tf`
- Create: `infra/variables.tf`
- Create: `infra/outputs.tf`

- [ ] **Step 1: Create `infra/main.tf`**

```hcl
terraform {
  required_version = ">= 1.5"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.aws_region
}
```

- [ ] **Step 2: Create `infra/variables.tf`**

```hcl
variable "aws_region" {
  description = "AWS deployment region"
  type        = string
  default     = "us-east-1"
}

variable "environment" {
  description = "Environment name tag"
  type        = string
  default     = "dev"
}

variable "app_password" {
  description = "Password for the app login gate"
  type        = string
  sensitive   = true
}

variable "image_tag" {
  description = "Docker image tag to deploy"
  type        = string
  default     = "latest"
}
```

- [ ] **Step 3: Create `infra/outputs.tf`**

```hcl
output "alb_url" {
  description = "URL of the application load balancer"
  value       = "http://${aws_lb.main.dns_name}"
}

output "s3_bucket_name" {
  description = "Name of the S3 bucket storing design files"
  value       = aws_s3_bucket.design_files.bucket
}

output "ecr_repository_url" {
  description = "URL of the ECR repository"
  value       = aws_ecr_repository.app.repository_url
}
```

- [ ] **Step 4: Commit**

```bash
git add infra/main.tf infra/variables.tf infra/outputs.tf
git commit -m "feat: add Terraform base config with provider, vars, outputs"
```

---

### Task 8: Terraform — VPC

**Files:**
- Create: `infra/vpc.tf`

- [ ] **Step 1: Create `infra/vpc.tf`**

```hcl
resource "aws_vpc" "main" {
  cidr_block           = "10.0.0.0/16"
  enable_dns_hostnames = true
  enable_dns_support   = true

  tags = { Name = "design-file-manager-${var.environment}" }
}

resource "aws_internet_gateway" "main" {
  vpc_id = aws_vpc.main.id
  tags   = { Name = "design-file-manager-${var.environment}" }
}

resource "aws_subnet" "public" {
  count                   = 2
  vpc_id                  = aws_vpc.main.id
  cidr_block              = "10.0.${count.index}.0/24"
  availability_zone       = data.aws_availability_zones.available.names[count.index]
  map_public_ip_on_launch = true

  tags = { Name = "design-file-manager-public-${count.index}" }
}

resource "aws_subnet" "private" {
  count             = 2
  vpc_id            = aws_vpc.main.id
  cidr_block        = "10.0.${count.index + 10}.0/24"
  availability_zone = data.aws_availability_zones.available.names[count.index]

  tags = { Name = "design-file-manager-private-${count.index}" }
}

resource "aws_eip" "nat" {
  domain = "vpc"
  tags   = { Name = "design-file-manager-${var.environment}" }
}

resource "aws_nat_gateway" "main" {
  allocation_id = aws_eip.nat.id
  subnet_id     = aws_subnet.public[0].id
  tags          = { Name = "design-file-manager-${var.environment}" }
}

resource "aws_route_table" "public" {
  vpc_id = aws_vpc.main.id

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.main.id
  }

  tags = { Name = "design-file-manager-public-${var.environment}" }
}

resource "aws_route_table_association" "public" {
  count          = 2
  subnet_id      = aws_subnet.public[count.index].id
  route_table_id = aws_route_table.public.id
}

resource "aws_route_table" "private" {
  vpc_id = aws_vpc.main.id

  route {
    cidr_block     = "0.0.0.0/0"
    nat_gateway_id = aws_nat_gateway.main.id
  }

  tags = { Name = "design-file-manager-private-${var.environment}" }
}

resource "aws_route_table_association" "private" {
  count          = 2
  subnet_id      = aws_subnet.private[count.index].id
  route_table_id = aws_route_table.private.id
}

data "aws_availability_zones" "available" {
  state = "available"
}

resource "aws_security_group" "alb" {
  name        = "design-file-manager-alb-${var.environment}"
  description = "Allow HTTP inbound"
  vpc_id      = aws_vpc.main.id

  ingress {
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = { Name = "design-file-manager-alb-${var.environment}" }
}

resource "aws_security_group" "ecs" {
  name        = "design-file-manager-ecs-${var.environment}"
  description = "Allow inbound from ALB only"
  vpc_id      = aws_vpc.main.id

  ingress {
    from_port       = 8000
    to_port         = 8000
    protocol        = "tcp"
    security_groups = [aws_security_group.alb.id]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = { Name = "design-file-manager-ecs-${var.environment}" }
}
```

- [ ] **Step 2: Commit**

```bash
git add infra/vpc.tf
git commit -m "feat: add Terraform VPC with public/private subnets, NAT, and security groups"
```

---

### Task 9: Terraform — S3 Bucket

**Files:**
- Create: `infra/s3.tf`

- [ ] **Step 1: Create `infra/s3.tf`**

```hcl
resource "aws_s3_bucket" "design_files" {
  bucket = "design-file-manager-${var.environment}-${data.aws_caller_identity.current.account_id}"

  tags = { Name = "design-file-manager-${var.environment}" }
}

resource "aws_s3_bucket_versioning" "design_files" {
  bucket = aws_s3_bucket.design_files.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "design_files" {
  bucket = aws_s3_bucket.design_files.id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_lifecycle_configuration" "design_files" {
  bucket = aws_s3_bucket.design_files.id

  rule {
    id     = "abort-incomplete-multipart"
    status = "Enabled"

    abort_incomplete_multipart_upload {
      days_after_initiation = 7
    }
  }
}

resource "aws_s3_bucket_policy" "design_files" {
  bucket = aws_s3_bucket.design_files.id
  policy = data.aws_iam_policy_document.bucket_policy.json
}

data "aws_iam_policy_document" "bucket_policy" {
  statement {
    sid       = "DenyNonSSL"
    effect    = "Deny"
    actions   = ["s3:*"]
    resources = [
      aws_s3_bucket.design_files.arn,
      "${aws_s3_bucket.design_files.arn}/*",
    ]
    principals {
      type        = "*"
      identifiers = ["*"]
    }
    condition {
      test     = "Bool"
      variable = "aws:SecureTransport"
      values   = ["false"]
    }
  }
}

data "aws_caller_identity" "current" {}

data "aws_iam_policy_document" "ecs_s3_access" {
  statement {
    sid    = "ECSS3ReadWrite"
    effect = "Allow"
    actions = [
      "s3:ListBucket",
      "s3:GetObject",
      "s3:PutObject",
      "s3:DeleteObject",
    ]
    resources = [
      aws_s3_bucket.design_files.arn,
      "${aws_s3_bucket.design_files.arn}/*",
    ]
  }
}
```

- [ ] **Step 2: Commit**

```bash
git add infra/s3.tf
git commit -m "feat: add Terraform S3 bucket with versioning, encryption, and IAM policies"
```

---

### Task 10: Terraform — ECR + ECS + ALB

**Files:**
- Create: `infra/ecr.tf`
- Create: `infra/ecs.tf`

- [ ] **Step 1: Create `infra/ecr.tf`**

```hcl
resource "aws_ecr_repository" "app" {
  name                 = "design-file-manager-${var.environment}"
  image_tag_mutability = "MUTABLE"

  image_scanning_configuration {
    scan_on_push = true
  }

  tags = { Name = "design-file-manager-${var.environment}" }
}

resource "aws_ecr_lifecycle_policy" "app" {
  repository = aws_ecr_repository.app.name

  policy = jsonencode({
    rules = [{
      rulePriority = 1
      description  = "Keep last 5 images"
      selection = {
        tagStatus   = "any"
        countType   = "imageCountMoreThan"
        countNumber = 5
      }
      action = { type = "expire" }
    }]
  })
}
```

- [ ] **Step 2: Create `infra/ecs.tf`**

```hcl
resource "aws_ecs_cluster" "main" {
  name = "design-file-manager-${var.environment}"
  tags = { Name = "design-file-manager-${var.environment}" }
}

resource "aws_ecs_task_definition" "app" {
  family                   = "design-file-manager-${var.environment}"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = "512"
  memory                   = "1024"
  execution_role_arn       = aws_iam_role.ecs_execution.arn
  task_role_arn            = aws_iam_role.ecs_task.arn

  container_definitions = jsonencode([
    {
      name  = "app"
      image = "${aws_ecr_repository.app.repository_url}:${var.image_tag}"
      portMappings = [
        { containerPort = 8000, protocol = "tcp" }
      ]
      environment = [
        { name = "S3_BUCKET", value = aws_s3_bucket.design_files.bucket },
        { name = "AWS_REGION", value = var.aws_region },
        { name = "APP_PASSWORD", value = var.app_password },
      ]
      logConfiguration = {
        logDriver = "awslogs"
        options = {
          "awslogs-group"         = "/ecs/design-file-manager-${var.environment}"
          "awslogs-region"        = var.aws_region
          "awslogs-stream-prefix" = "ecs"
        }
      }
    }
  ])

  tags = { Name = "design-file-manager-${var.environment}" }
}

resource "aws_ecs_service" "app" {
  name            = "design-file-manager-${var.environment}"
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.app.arn
  desired_count   = 1
  launch_type     = "FARGATE"

  network_configuration {
    subnets         = aws_subnet.private[*].id
    security_groups = [aws_security_group.ecs.id]
    assign_public_ip = false
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.app.arn
    container_name   = "app"
    container_port   = 8000
  }

  depends_on = [aws_lb_listener.main]
  tags       = { Name = "design-file-manager-${var.environment}" }
}

resource "aws_lb" "main" {
  name               = "design-file-manager-${var.environment}"
  internal           = false
  load_balancer_type = "application"
  security_groups    = [aws_security_group.alb.id]
  subnets            = aws_subnet.public[*].id
  tags               = { Name = "design-file-manager-${var.environment}" }
}

resource "aws_lb_target_group" "app" {
  name        = "design-file-manager-${var.environment}"
  port        = 8000
  protocol    = "HTTP"
  vpc_id      = aws_vpc.main.id
  target_type = "ip"

  health_check {
    path                = "/"
    matcher             = "200,303"
    interval            = 30
    timeout             = 5
    healthy_threshold   = 2
    unhealthy_threshold = 3
  }

  tags = { Name = "design-file-manager-${var.environment}" }
}

resource "aws_lb_listener" "main" {
  load_balancer_arn = aws_lb.main.arn
  port              = 80
  protocol          = "HTTP"

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.app.arn
  }
}

resource "aws_cloudwatch_log_group" "ecs" {
  name              = "/ecs/design-file-manager-${var.environment}"
  retention_in_days = 7
  tags              = { Name = "design-file-manager-${var.environment}" }
}

resource "aws_iam_role" "ecs_execution" {
  name = "design-file-manager-ecs-execution-${var.environment}"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Principal = { Service = "ecs-tasks.amazonaws.com" }
      Action = "sts:AssumeRole"
    }]
  })
}

resource "aws_iam_role_policy_attachment" "ecs_execution" {
  role       = aws_iam_role.ecs_execution.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

resource "aws_iam_role" "ecs_task" {
  name = "design-file-manager-ecs-task-${var.environment}"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Principal = { Service = "ecs-tasks.amazonaws.com" }
      Action = "sts:AssumeRole"
    }]
  })
}

resource "aws_iam_role_policy" "ecs_task_s3" {
  role   = aws_iam_role.ecs_task.name
  name   = "s3-access"
  policy = data.aws_iam_policy_document.ecs_s3_access.json
}
```

- [ ] **Step 3: Commit**

```bash
git add infra/ecr.tf infra/ecs.tf
git commit -m "feat: add Terraform ECR, ECS, ALB, and IAM roles"
```

---

## Self-Review Checklist

### 1. Spec coverage
All spec requirements have tasks:
- ✅ Auth module (Task 2)
- ✅ S3 CRUD operations (Task 3)
- ✅ FastAPI routes with middleware (Task 4)
- ✅ Templates (Task 5)
- ✅ Static CSS (Task 6)
- ✅ Terraform base (Task 7)
- ✅ VPC with subnets, NAT, SGs (Task 8)
- ✅ S3 bucket with versioning, encryption, lifecycle (Task 9)
- ✅ ECR, ECS, ALB, IAM (Task 10)
- ✅ Dockerfile + Makefile + docker-compose (Task 1)

### 2. Placeholder scan
- No TBDs, TODOs, or vague instructions
- Every step has complete code
- Every test has complete assertions

### 3. Type consistency
- `create_session_token(password, secret)` and `verify_session_token(token, password, secret)` — consistent across auth.py and test_auth.py
- S3 functions all take `bucket_name` as last parameter — consistent
- Template variable names match route handler context — consistent

### 4. No missing steps
Dockerfile copies `app/` as working directory, but `main.py` does `from .auth import ...` — only works if `app/` is a package. The `__init__.py` is created in Task 1, and Dockerfile's WORKDIR is `/app` with `COPY . .` — correct.
