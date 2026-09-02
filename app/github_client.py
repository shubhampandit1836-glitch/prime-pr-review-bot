import httpx

from app.config import get_settings
from app.github_auth import generate_app_jwt

GITHUB_API_BASE = "https://api.github.com"


async def get_installation_access_token(installation_id: int) -> str:
    """
    Trade our app-wide JWT for a short-lived (1 hour) installation access
    token scoped to one specific installation. This is the token that
    can actually read/write repos — the JWT alone cannot call most
    endpoints, it can only request this exchange.
    """
    app_jwt = generate_app_jwt()

    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{GITHUB_API_BASE}/app/installations/{installation_id}/access_tokens",
            headers={
                "Authorization": f"Bearer {app_jwt}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
            },
        )
        response.raise_for_status()
        return response.json()["token"]


async def get_pr_diff(installation_id: int, repo_full_name: str, pr_number: int) -> str:
    """
    Fetch the actual unified diff for a pull request, using the special
    'diff' media type GitHub supports on the PR endpoint — this returns
    raw diff text directly, instead of us having to fetch each changed
    file's contents separately and construct a diff ourselves.
    """
    token = await get_installation_access_token(installation_id)

    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{GITHUB_API_BASE}/repos/{repo_full_name}/pulls/{pr_number}",
            headers={
                "Authorization": f"Bearer {token}",
                "Accept": "application/vnd.github.v3.diff",
                "X-GitHub-Api-Version": "2022-11-28",
            },
        )
        response.raise_for_status()
        return response.text
    
async def get_file_content(
    installation_id: int, repo_full_name: str, file_path: str, ref: str
) -> str:
    """
    Fetch the full raw content of one file at a specific commit (ref) —
    needed because AST parsing requires the complete file, not just the
    changed lines a diff shows. 'ref' should be the PR's head commit SHA,
    so we parse the file exactly as it exists in the proposed change.
    """
    token = await get_installation_access_token(installation_id)

    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{GITHUB_API_BASE}/repos/{repo_full_name}/contents/{file_path}",
            params={"ref": ref},
            headers={
                "Authorization": f"Bearer {token}",
                "Accept": "application/vnd.github.raw+json",
                "X-GitHub-Api-Version": "2022-11-28",
            },
        )
        response.raise_for_status()
        return response.text