import logging

from fastapi import FastAPI, Header, HTTPException, Request, status

from app.config import get_settings
from app.github_client import get_pr_diff
from app.github_events import PullRequestWebhookPayload
from app.security import verify_github_signature

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("pr_review_bot")

app = FastAPI(title="PR Review Bot")

RELEVANT_ACTIONS = {"opened", "synchronize", "reopened"}


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}


@app.post("/webhook", status_code=status.HTTP_202_ACCEPTED)
async def github_webhook(
    request: Request,
    x_hub_signature_256: str | None = Header(default=None),
    x_github_event: str | None = Header(default=None),
) -> dict:
    settings = get_settings()

    raw_body = await request.body()

    if not verify_github_signature(raw_body, x_hub_signature_256, settings.github_webhook_secret):
        logger.warning("Rejected webhook delivery with invalid signature")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid signature")

    if x_github_event == "ping":
        logger.info("Received GitHub ping event — webhook is configured correctly")
        return {"status": "pong"}

    if x_github_event != "pull_request":
        logger.info("Ignoring event type: %s", x_github_event)
        return {"status": "ignored", "reason": "not a pull_request event"}

    payload = PullRequestWebhookPayload.model_validate_json(raw_body)

    if payload.action not in RELEVANT_ACTIONS:
        logger.info("Ignoring pull_request action: %s", payload.action)
        return {"status": "ignored", "reason": f"action '{payload.action}' not relevant"}

    if payload.pull_request.draft:
        logger.info("Ignoring draft PR #%s", payload.number)
        return {"status": "ignored", "reason": "draft PR"}

    logger.info(
        "Accepted PR event: repo=%s pr=#%s action=%s title=%r",
        payload.repository.full_name, payload.number, payload.action, payload.pull_request.title,
    )

    # Step 2: fetch the real diff now that we have an installation ID.
    diff = await get_pr_diff(
        installation_id=payload.installation.id,
        repo_full_name=payload.repository.full_name,
        pr_number=payload.number,
    )
    logger.info("Fetched diff for PR #%s — %d characters", payload.number, len(diff))

    # Step 3 picks up here: parse this diff with tree-sitter to extract
    # AST-aware context around each changed hunk. Not built yet.

    return {"status": "accepted", "pr": payload.number, "diff_length": len(diff)}