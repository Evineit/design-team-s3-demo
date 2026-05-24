import os
import pytest
from itsdangerous import URLSafeTimedSerializer


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
    from moto import mock_aws
    import boto3
    with mock_aws():
        yield boto3.client("s3", region_name="us-east-1")


@pytest.fixture
def bucket_name():
    return "test-design-bucket"


@pytest.fixture
def s3_bucket(s3_mock, bucket_name):
    s3_mock.create_bucket(Bucket=bucket_name)
    return s3_mock
