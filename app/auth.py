import time
from itsdangerous import URLSafeTimedSerializer


def _make_serializer(secret):
    return URLSafeTimedSerializer(secret, salt="auth")


def create_session_token(password, secret, max_age=86400):
    serializer = _make_serializer(secret)
    expires = time.time() + max_age
    return serializer.dumps({"p": password, "expires": expires})


def verify_session_token(token, expected_password, secret):
    try:
        serializer = _make_serializer(secret)
        data = serializer.loads(token)
        if time.time() > data.get("expires", 0):
            return False
        return data.get("p") == expected_password
    except Exception:
        return False
