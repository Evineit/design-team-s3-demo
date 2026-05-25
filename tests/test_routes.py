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
