import time
from pathlib import Path

import jwt

from app.config import get_settings


def _load_private_key() -> str:
    """
    Read the .pem file from disk. A separate function so it's easy to
    mock in tests later, instead of hardcoding file I/O directly into
    the JWT generation logic below.
    """
    settings = get_settings()
    key_path = Path(settings.github_private_key_path)
    if not key_path.exists():
        raise FileNotFoundError(
            f"GitHub App private key not found at '{key_path}'. "
            "Download it from your App's settings page and place it there."
        )
    return key_path.read_text()


def generate_app_jwt() -> str:
    """
    Build a short-lived JWT that authenticates as the GitHub App itself
    (not any specific installation). GitHub requires:
      - iat: issued-at time, backdated by 60s to tolerate clock drift
        between this machine and GitHub's servers
      - exp: expiry, max allowed is 10 minutes from iat
      - iss: the App ID, telling GitHub which app this JWT claims to be
    Signed with RS256 using our private key; GitHub verifies it against
    the public key it already has on file for this App.
    """
    settings = get_settings()
    private_key = _load_private_key()

    now = int(time.time())
    payload = {
        "iat": now - 60,
        "exp": now + (9 * 60),  # 9 minutes, safely under GitHub's 10-minute max
        "iss": settings.github_app_id,
    }

    return jwt.encode(payload, private_key, algorithm="RS256")