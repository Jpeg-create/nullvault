"""Standalone client for fetching secrets from a running NullVault instance.

Copy this file into another project (no dependencies beyond the Python
standard library) and call get_secret(project, name) at startup instead of
storing the real value in that project's own .env file.

Example:

    from client import get_secret

    DATABASE_PASSWORD = get_secret("acme-app", "database-password")

The project token is read from the NULLVAULT_TOKEN environment variable by
default. Generate one with:

    POST /projects/{project}/token

using an account-level login token, and store the result as NULLVAULT_TOKEN
in the consuming project's own environment. That token only ever unlocks
secrets belonging to the one project it was issued for.
"""

import json
import os
import urllib.error
import urllib.request

DEFAULT_BASE_URL = "http://127.0.0.1:8100"


class NullVaultError(RuntimeError):
    """Raised when a secret cannot be fetched from NullVault."""


def get_secret(project: str, name: str, token: str = None, base_url: str = None) -> str:
    """Fetch and decrypt one secret from NullVault.

    project: the project slug the secret was submitted under.
    name: the secret's name.
    token: a project-scoped access token. Defaults to the NULLVAULT_TOKEN
        environment variable if not given.
    base_url: the NullVault API base URL. Defaults to the NULLVAULT_URL
        environment variable, then to http://127.0.0.1:8100.

    Raises NullVaultError if no token is available or the request fails.
    """
    token = token or os.environ.get("NULLVAULT_TOKEN")
    if not token:
        raise NullVaultError(
            "No NullVault token provided. Pass token= explicitly or set the "
            "NULLVAULT_TOKEN environment variable."
        )

    base_url = (base_url or os.environ.get("NULLVAULT_URL") or DEFAULT_BASE_URL).rstrip("/")
    url = f"{base_url}/secrets/{project}/{name}"

    request = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"})

    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            payload = json.loads(response.read().decode())
    except urllib.error.HTTPError as exc:
        raise NullVaultError(
            f"NullVault returned {exc.code} for {project}/{name}: {exc.reason}"
        ) from exc
    except urllib.error.URLError as exc:
        raise NullVaultError(f"Could not reach NullVault at {base_url}: {exc.reason}") from exc

    return payload["value"]


if __name__ == "__main__":
    import sys

    if len(sys.argv) != 3:
        print("usage: python client.py <project> <secret-name>", file=sys.stderr)
        raise SystemExit(1)

    print(get_secret(sys.argv[1], sys.argv[2]))
