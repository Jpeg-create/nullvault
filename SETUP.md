# NullVault Setup

This describes how NullVault is deployed on this VPS, how to hand off a secret from a
client, and how to roll back if something breaks.

## What's running where

NullVault runs as two isolated Docker containers, separate from every other service on
this host:

| Container | Image | Network | Exposed to |
| --- | --- | --- | --- |
| `nullvault-api` | built from this repo's `Dockerfile` | `nullvault-net` (bridge) | `127.0.0.1:8100` only |
| `nullvault-db` | `postgres:16` | `nullvault-net` (bridge) | nothing, no host port |

Both containers sit on their own Docker bridge network (`nullvault_nullvault-net`),
separate from any other per-service networks you may run on the same host.
The API can only be reached from the VPS itself (`127.0.0.1:8100`), never directly
from the internet. Postgres has no host port at all; only `nullvault-api` can reach
it, over the internal network, by hostname `nullvault-db`.

Public access comes through nginx as a reverse proxy on `https://vault.yourdomain.com`
(replace with whatever subdomain you point at this deployment), terminating HTTPS at
this server and forwarding to `127.0.0.1:8100`. The vhost is installed at
`/etc/nginx/sites-available/vault.yourdomain.com` (symlinked into `sites-enabled`);
the copy in this repo is `deploy/nginx-vault.yourdomain.com.conf`. If you're proxying
through Cloudflare, it terminates HTTPS for visitors, and the connection from
Cloudflare to this server is also HTTPS, using a Cloudflare Origin CA certificate
installed at `/etc/nginx/ssl/yourdomain-origin.pem` and `.key` (issue one scoped to
your subdomain, or to your whole domain, valid for up to 15 years).

### Files

- `Dockerfile` - builds the API image (Python 3.11-slim, installs `requirements.txt`,
  runs `uvicorn app.main:app` on port 8000 inside the container).
- `docker-compose.yml` - defines both containers, the network, and the Postgres data
  volume (`nullvault_pgdata`).
- `.env` - real secrets for this deployment (`SECRET_KEY`, `ENCRYPTION_KEY`,
  `DB_PASSWORD`, `DATABASE_URL`). Not committed to git, listed in `.gitignore`. If you
  ever need to rotate a key, edit `.env` and run `docker compose up -d --build` to pick
  it up. Rotating `ENCRYPTION_KEY` will make existing encrypted secrets unreadable,
  since Fernet decryption requires the same key that encrypted the data.
- `static/submit.html` - the client-facing secret handoff page, served at `/submit`.
- `client.py` - standalone, dependency-free client for other codebases to fetch their
  own secrets at runtime with `get_secret(project, name)`. Meant to be copied into
  another project, not run from here.
- `deploy/nginx-vault.yourdomain.com.conf` - the nginx vhost for the public subdomain
  (rename to match your actual subdomain).

## Projects

Secrets in NullVault always belong to a project, not just to your account. One
account can own many projects (one per client, one per app, however you want to split
it), and each project's secrets are invisible to every other project, even ones you
own. This is what lets you hand a client or an external codebase a token that only
ever sees the one project it was made for.

There are two kinds of token:

- **Account tokens** (from `/auth/login`) can create projects, list your projects,
  and mint project tokens. They can also read and write secrets in any project you
  own. Use these for yourself.
- **Project tokens** (from `POST /projects/{project}/token`) are scoped to exactly
  one project. They cannot create projects, list other projects, or touch any
  project's secrets besides their own. Use these for clients and for other codebases.

Project tokens default to a much longer lifetime than account tokens
(`PROJECT_TOKEN_EXPIRE_MINUTES`, about a year), since they are meant to sit in
another codebase's environment rather than be regenerated constantly. Account tokens
still expire quickly (`ACCESS_TOKEN_EXPIRE_MINUTES`, 30 minutes by default).

Create a project and a token for it from your own account token:
```bash
curl -X POST http://127.0.0.1:8100/projects/ \
  -H "Authorization: Bearer <your account token>" \
  -H "Content-Type: application/json" \
  -d '{"name": "acme-app"}'

curl -X POST http://127.0.0.1:8100/projects/acme-app/token \
  -H "Authorization: Bearer <your account token>"
```

## Adding a new client's secret

Clients hand off one API key or credential at a time through `/submit`, without ever
seeing this server or any secret besides the one they're submitting.

1. Create a project for the client if one doesn't exist yet, and generate a project
   token for it (see [Projects](#projects) above). Use a name that identifies the
   client or app, e.g. `acme-app`.

2. Send the client this link, the project name, and the project token:
   `https://vault.yourdomain.com/submit`

3. The client pastes the token, enters the project name, a name for the secret (e.g.
   `stripe-api-key`), and the value, then submits. The value is encrypted immediately
   server-side and the page never shows it back. You are not in the loop and never
   see the raw value in transit. Because the token is scoped to that one project, the
   client cannot see or overwrite any other project's secrets even if they guess a
   different project name.

4. To retrieve what they submitted:
   ```bash
   curl http://127.0.0.1:8100/secrets/acme-app/stripe-api-key \
     -H "Authorization: Bearer <your account token, or that project's token>"
   ```

## Using a secret from another codebase

This is the other half of project scoping: instead of a human submitting a secret
through the browser, another app fetches its own secret at runtime and never stores
the real value in its own `.env` file.

1. Create a project and a project token for that app the same way as above.
2. In the other app's environment (its process environment, secret manager, or CI
   variables, never a `.env` file next to real credentials), set:
   ```
   NULLVAULT_TOKEN=<the project token>
   NULLVAULT_URL=https://vault.yourdomain.com
   ```
   If the other app runs on this same host, `http://127.0.0.1:8100` also works and
   avoids a round trip through the public internet.
3. Copy [`client.py`](client.py) into that app's codebase. It has no dependencies
   beyond the Python standard library:
   ```python
   from client import get_secret

   database_password = get_secret("acme-app", "database-password")
   ```

`get_secret` reads `NULLVAULT_TOKEN` and `NULLVAULT_URL` from the environment by
default, so most call sites don't need to pass them explicitly.

## Rolling back

Everything needed to roll back lives in Docker, so nothing here touches system Python
or system packages.

- **Restart just the API** (e.g. after a bad code change):
  ```bash
  cd /path/to/nullvault
  git log --oneline          # find the last good commit
  git checkout <commit> -- app/   # restore just the app code
  docker compose up -d --build nullvault-api
  ```

- **Full stack restart** (containers misbehaving, config changed):
  ```bash
  cd /path/to/nullvault
  docker compose down
  docker compose up -d --build
  ```
  This keeps the Postgres data volume (`nullvault_pgdata`), so no secrets are lost.

- **Wipe and start fresh** (only if you want to lose all stored secrets, e.g. this was
  a test deployment):
  ```bash
  cd /path/to/nullvault
  docker compose down
  docker volume rm nullvault_nullvault_pgdata
  docker compose up -d --build
  ```

- **Reverse proxy rollback:** if the nginx vhost breaks the rest of the server,
  disable just this site without touching anything else:
  ```bash
  rm /etc/nginx/sites-enabled/vault.yourdomain.com
  nginx -t && systemctl reload nginx
  ```
  The API keeps running on `127.0.0.1:8100` either way; this only affects public
  access through the subdomain.

- **Check logs** when something looks wrong:
  ```bash
  docker logs nullvault-api --tail 100
  docker logs nullvault-db --tail 100
  ```

## Running the test suite again

```bash
cd /path/to/nullvault
docker compose run --rm -v "$(pwd)/tests:/app/tests:ro" nullvault-api pytest tests/ -v
```

This runs the tests in a throwaway container against the real, running Postgres
container, the same way they were verified during setup.
