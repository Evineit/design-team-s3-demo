import io
import pytest
from app.s3_client import create_bucket, list_files, upload_file, download_file, delete_file


class TestCreateBucket:
    def test_creates_new_bucket(self, s3_mock):
        create_bucket("fresh-test-bucket")
        buckets = s3_mock.list_buckets()["Buckets"]
        assert any(b["Name"] == "fresh-test-bucket" for b in buckets)

    def test_idempotent_when_bucket_exists(self, s3_bucket, bucket_name):
        create_bucket(bucket_name)


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
