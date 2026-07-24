# NullVault

A secure secrets and API key management REST API built with FastAPI, PostgreSQL, and JWT authentication.

[![tests](https://github.com/Jpeg-create/nullvault/actions/workflows/tests.yml/badge.svg)](https://github.com/Jpeg-create/nullvault/actions/workflows/tests.yml)
![Python](https://img.shields.io/badge/python-3.8+-blue.svg)
![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-green.svg)
![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)

## What is NullVault?

NullVault lets developers securely store, retrieve, and manage API keys and secrets through a REST API. Secrets are organized into projects, so one account can hold credentials for several separate apps or clients without them being visible to each other. Secrets are encrypted at rest using Fernet symmetric encryption, and every action is logged in an audit trail.

## Features

- **JWT Authentication** — register and login, every endpoint is protected
- **Project Scoping** — secrets belong to a project, not just a flat account; one user can own many projects
- **Project Tokens** — generate a token scoped to a single project, so an external app or client can fetch only its own secrets
- **Encrypted Secrets** — secrets stored encrypted, never in plaintext
- **Audit Logging** — every read, write, and delete is recorded with timestamp and project
- **Security by Design** — list endpoint never returns secret values, only names

## Tech Stack

- FastAPI — REST API framework
- PostgreSQL — database
- SQLAlchemy — ORM
- JWT (python-jose) — authentication tokens
- cryptography (Fernet) — secret encryption
- passlib + bcrypt — password hashing

## API Endpoints

| Method | Endpoint | Description | Auth Required |
| --- | --- | --- | --- |
| POST | /auth/register | Create account | No |
| POST | /auth/login | Get JWT token | No |
| POST | /projects/ | Create a project | Yes (account token) |
| GET | /projects/ | List your projects | Yes (account token) |
| POST | /projects/{project}/token | Generate a token scoped to one project | Yes (account token) |
| POST | /secrets/ | Store a secret (project specified in the request body) | Yes |
| GET | /secrets/ | List secrets, optionally filtered with `?project=` | Yes |
| GET | /secrets/{project}/{name} | Retrieve a decrypted secret | Yes |
| DELETE | /secrets/{project}/{name} | Delete a secret | Yes |
| GET | /audit/ | View audit log, optionally filtered with `?project=` | Yes |
| GET | /health | Health check | No |
| GET | /submit | Client-facing secret handoff form (paste a token, pick a project, submit one secret by name and value) | No (form itself; submitting requires a valid token) |

Account tokens (from `/auth/login`) can manage projects and act on any project you own. Project tokens (from `/projects/{project}/token`) can only read and write secrets within that one project, and cannot create projects or mint other tokens.

## Getting Started

### 1. Clone the repo
```bash
git clone https://github.com/Jpeg-create/nullvault.git
cd nullvault
```

### 2. Install dependencies
```bash
pip install -r requirements.txt
```

### 3. Set up PostgreSQL and create a database
```bash
createdb nullvault
```

### 4. Configure environment variables
```bash
cp .env.example .env
```

Edit `.env` with your values:
```
DATABASE_URL=postgresql://your_user@localhost:5432/nullvault
SECRET_KEY=your-secret-key
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
ENCRYPTION_KEY=your-fernet-key
```

Generate a Fernet key:
```bash
python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

### 5. Run the API
```bash
uvicorn app.main:app --reload
```

## Using NullVault from Another Codebase

The point of project scoping is to let another app fetch its own secrets at runtime
instead of storing them in its own `.env` file.

1. Create a project and generate a token scoped to it:
   ```bash
   curl -X POST http://127.0.0.1:8000/projects/ \
     -H "Authorization: Bearer <your account token>" \
     -H "Content-Type: application/json" \
     -d '{"name": "acme-app"}'

   curl -X POST http://127.0.0.1:8000/projects/acme-app/token \
     -H "Authorization: Bearer <your account token>"
   ```
   The response's `access_token` only ever unlocks secrets belonging to `acme-app`.
   It cannot see other projects, create new projects, or mint further tokens.

2. Store that token as `NULLVAULT_TOKEN` in the other project's environment (its
   process environment, secret manager, or CI variables, not a `.env` file that ends
   up next to real credentials).

3. Copy [`client.py`](client.py) into that project. It has no dependencies beyond the
   Python standard library, so it drops into any codebase as-is:
   ```python
   from client import get_secret

   database_password = get_secret("acme-app", "database-password")
   ```
   `get_secret` reads `NULLVAULT_TOKEN` (and optionally `NULLVAULT_URL`) from the
   environment, calls NullVault, and returns the decrypted value. The other project
   never stores the real secret on disk.

## Production Deployment

NullVault can also be run as an isolated Docker service, sitting behind nginx with
HTTPS, on its own network and with no ports exposed beyond the API itself. This is a
convenient setup for handing off an API key or credential from a client: you generate
them a short-lived token, they open a link, paste the token, and submit the secret
through `/submit`, without ever needing access to the server. See
[SETUP.md](SETUP.md) for the full walkthrough, including the Dockerfile, docker-compose
setup, reverse proxy configuration, and rollback steps.

## License

MIT

