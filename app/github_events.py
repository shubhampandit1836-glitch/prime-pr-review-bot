from pydantic import BaseModel


class Repository(BaseModel):
    full_name: str  # e.g. "octocat/hello-world"


class PullRequestRef(BaseModel):
    number: int
    title: str
    draft: bool = False


class PullRequestWebhookPayload(BaseModel):
    """
    Subset of GitHub's pull_request event payload. We deliberately model
    only the fields this app actually uses (Pydantic ignores the rest) —
    modeling GitHub's entire ~80-field payload up front would be dead
    weight we'd have to maintain against API changes we don't care about.
    """

    action: str  # "opened", "synchronize", "reopened", etc.
    number: int
    pull_request: PullRequestRef
    repository: Repository