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
