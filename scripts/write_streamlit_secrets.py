"""Create Streamlit's OIDC config from deployment secret environment values."""

import json
import os
from pathlib import Path
import sys
from urllib.parse import urlparse


REQUIRED = (
    "BIZPILOT_PUBLIC_URL",
    "OIDC_CLIENT_ID",
    "OIDC_CLIENT_SECRET",
    "OIDC_COOKIE_SECRET",
)


def main() -> int:
    missing = [name for name in REQUIRED if not os.getenv(name, "").strip()]
    if missing:
        print("Missing required OIDC deployment settings: " + ", ".join(missing), file=sys.stderr)
        return 1

    public_url = os.environ["BIZPILOT_PUBLIC_URL"].strip().rstrip("/")
    parsed = urlparse(public_url)
    if parsed.scheme != "https" or not parsed.netloc or parsed.query or parsed.fragment:
        print("BIZPILOT_PUBLIC_URL must be an HTTPS origin without query or fragment.", file=sys.stderr)
        return 1

    values = {
        "redirect_uri": f"{public_url}/oauth2callback",
        "cookie_secret": os.environ["OIDC_COOKIE_SECRET"],
        "client_id": os.environ["OIDC_CLIENT_ID"],
        "client_secret": os.environ["OIDC_CLIENT_SECRET"],
        "server_metadata_url": "https://accounts.google.com/.well-known/openid-configuration",
    }
    destination = Path(".streamlit/secrets.toml")
    destination.parent.mkdir(parents=True, exist_ok=True)
    lines = ["[auth]", *(f"{key} = {json.dumps(value)}" for key, value in values.items())]
    destination.write_text("\n".join(lines) + "\n", encoding="utf-8")
    try:
        destination.chmod(0o600)
    except OSError:
        pass
    print("Streamlit OIDC configuration created without displaying secret values.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
