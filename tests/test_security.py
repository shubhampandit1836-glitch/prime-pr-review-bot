import hashlib
import hmac

from app.security import verify_github_signature

SECRET = "test-webhook-secret"
BODY = b'{"action": "opened", "number": 1}'


def _sign(body: bytes, secret: str) -> str:
    digest = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    return f"sha256={digest}"


def test_valid_signature_is_accepted():
    header = _sign(BODY, SECRET)
    assert verify_github_signature(BODY, header, SECRET) is True


def test_wrong_secret_is_rejected():
    header = _sign(BODY, "a-different-secret")
    assert verify_github_signature(BODY, header, SECRET) is False


def test_tampered_body_is_rejected():
    # Signature was computed over BODY, but the body that "arrived" was
    # modified in transit — exactly what signature verification exists to catch.
    header = _sign(BODY, SECRET)
    tampered_body = b'{"action": "opened", "number": 999}'
    assert verify_github_signature(tampered_body, header, SECRET) is False


def test_missing_header_is_rejected():
    assert verify_github_signature(BODY, None, SECRET) is False


def test_malformed_header_is_rejected():
    assert verify_github_signature(BODY, "not-even-close-to-valid", SECRET) is False


def test_empty_string_header_is_rejected():
    assert verify_github_signature(BODY, "", SECRET) is False