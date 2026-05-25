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

SESSION_COOKIE = "session"


def _s3_bucket():
    return os.environ.get("S3_BUCKET", "design-file-manager")


def _app_password():
    return os.environ.get("APP_PASSWORD", "admin")


class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        public_paths = {"/login", "/static"}
        if request.url.path in public_paths or request.url.path.startswith("/static/"):
            return await call_next(request)
        token = request.cookies.get(SESSION_COOKIE)
        if not token or not verify_session_token(token, _app_password(), _app_password()):
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
    if password != _app_password():
        return templates.TemplateResponse(
            "login.html", {"request": request, "error": "Incorrect password"}, status_code=200
        )
    token = create_session_token(password, _app_password())
    from .s3_client import list_files
    files = list_files(_s3_bucket())
    resp = templates.TemplateResponse("index.html", {"request": request, "files": files})
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

    files = list_files(_s3_bucket())
    return templates.TemplateResponse("index.html", {"request": request, "files": files})


@app.post("/upload")
async def upload(request: Request, file: UploadFile = File(...), file_type: str = Form("designs")):
    from .s3_client import upload_file, list_files

    contents = await file.read()
    import io
    buf = io.BytesIO(contents)
    key = f"{file_type}/{file.filename}"
    upload_file(buf, key, _s3_bucket())
    files = list_files(_s3_bucket())
    return templates.TemplateResponse("index.html", {"request": request, "files": files})


@app.get("/download/{key:path}")
async def download(key: str):
    from .s3_client import download_file

    try:
        buf = download_file(key, _s3_bucket())
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

    delete_file(key, _s3_bucket())
    return RedirectResponse(url="/", status_code=303)
