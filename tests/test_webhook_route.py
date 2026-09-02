import hashlib
import hmac
import json

import pytest
from fastapi.testclient import TestClient

from app.config import get_settings
from app.main import app

SECRET = "test-webhook-secret"


@pytest.fixture(autouse=True)
def _override_settings(monkeypatch):
    monkeypatch.setenv("GITHUB_WEBHOOK_SECRET", SECRET)
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


client = TestClient(app)


def _signed_headers(body: bytes, event: str) -> dict:
    digest = hmac.new(SECRET.encode(), body, hashlib.sha256).hexdigest()
    return {
        "X-Hub-Signature-256": f"sha256={digest}",
        "X-GitHub-Event": event,
        "Content-Type": "application/json",
    }


def _pr_payload(action: str = "opened", draft: bool = False) -> bytes:
    return json.dumps({
        "action": action,
        "number": 42,
        "pull_request": {"number": 42, "title": "Add feature", "draft": draft},
        "repository": {"full_name": "octocat/hello-world"},
    }).encode()


def test_rejects_missing_signature():
    body = _pr_payload()
    resp = client.post("/webhook", content=body, headers={"X-GitHub-Event": "pull_request"})
    assert resp.status_code == 401


def test_rejects_invalid_signature():
    body = _pr_payload()
    headers = _signed_headers(body, "pull_request")
    headers["X-Hub-Signature-256"] = "sha256=" + "0" * 64
    resp = client.post("/webhook", content=body, headers=headers)
    assert resp.status_code == 401


def test_accepts_valid_pr_opened():
    body = _pr_payload(action="opened")
    resp = client.post("/webhook", content=body, headers=_signed_headers(body, "pull_request"))
    assert resp.status_code == 202
    assert resp.json() == {"status": "accepted", "pr": 42}


def test_accepts_synchronize():
    body = _pr_payload(action="synchronize")
    resp = client.post("/webhook", content=body, headers=_signed_headers(body, "pull_request"))
    assert resp.json()["status"] == "accepted"


def test_ignores_irrelevant_action():
    body = _pr_payload(action="labeled")
    resp = client.post("/webhook", content=body, headers=_signed_headers(body, "pull_request"))
    assert resp.json()["status"] == "ignored"


def test_ignores_draft_pr():
    body = _pr_payload(action="opened", draft=True)
    resp = client.post("/webhook", content=body, headers=_signed_headers(body, "pull_request"))
    assert resp.json() == {"status": "ignored", "reason": "draft PR"}


def test_ignores_non_pull_request_event():
    body = json.dumps({"action": "created"}).encode()
    resp = client.post("/webhook", content=body, headers=_signed_headers(body, "issue_comment"))
    assert resp.json()["status"] == "ignored"


def test_ping_event_returns_pong():
    body = json.dumps({"zen": "Keep it logically awesome."}).encode()
    resp = client.post("/webhook", content=body, headers=_signed_headers(body, "ping"))
    assert resp.json() == {"status": "pong"}