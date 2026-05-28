#!/usr/bin/env python3
"""Seed LocalStack S3 with demo files for the showcase."""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "app"))

from s3_client import create_bucket, upload_file

BUCKET = os.environ.get("S3_BUCKET", "design-file-manager-local")
ENDPOINT = os.environ.get("AWS_ENDPOINT_URL", "http://localhost:4566")

os.environ.setdefault("AWS_ACCESS_KEY_ID", "fake")
os.environ.setdefault("AWS_SECRET_ACCESS_KEY", "fake")
os.environ.setdefault("AWS_DEFAULT_REGION", "us-east-1")
os.environ["AWS_ENDPOINT_URL"] = ENDPOINT

DEMO_DIR = Path(__file__).resolve().parent / "demo-files"

DEMO_FILES = {
    "designs/logo.svg": DEMO_DIR / "logo.svg",
    "designs/banner.svg": DEMO_DIR / "banner.svg",
    "backups/project-assets-backup.txt": DEMO_DIR / "project-assets-backup.txt",
}


def seed():
    print(f"Creating bucket: {BUCKET}")
    create_bucket(BUCKET)
    print("Bucket ready.")

    for key, path in DEMO_FILES.items():
        print(f"  Uploading {key} ({path.stat().st_size} bytes)")
        with open(path, "rb") as f:
            upload_file(f, key, BUCKET)

    print(f"\nDone! {len(DEMO_FILES)} files uploaded to '{BUCKET}'.")
    print(f"App should be running at http://localhost:8000")


if __name__ == "__main__":
    seed()
