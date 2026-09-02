import hashlib
import hmac


def verify_github_signature(payload_body: bytes, signature_header: str | None, secret: str) -> bool:
    """
    Verify a GitHub webhook delivery against its X-Hub-Signature-256 header.

    GitHub computes: "sha256=" + HMAC_SHA256(secret, raw_request_body).hex()
    We recompute the same digest and compare with hmac.compare_digest,
    which is constant-time — a plain `==` here would leak timing info
    an attacker could use to forge a valid signature byte-by-byte.

    Returns False (never raises) on any malformed input — a webhook
    endpoint should reject bad requests, not 500 on them.
    """
    if not signature_header or not signature_header.startswith("sha256="):
        return False

    their_digest = signature_header.removeprefix("sha256=")

    our_digest = hmac.new(
        key=secret.encode("utf-8"),
        msg=payload_body,
        digestmod=hashlib.sha256,
    ).hexdigest()

    return hmac.compare_digest(their_digest, our_digest)