import io
import os
import boto3


def _client():
    endpoint_url = os.environ.get("AWS_ENDPOINT_URL")
    kwargs = {}
    if endpoint_url:
        kwargs["endpoint_url"] = endpoint_url
    return boto3.client("s3", **kwargs)


def create_bucket(bucket_name):
    client = _client()
    try:
        client.create_bucket(Bucket=bucket_name)
    except client.exceptions.BucketAlreadyOwnedByYou:
        pass


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
