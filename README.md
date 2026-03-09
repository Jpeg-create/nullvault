# NullVault

A secure secrets and API key management REST API built with FastAPI, PostgreSQL, and JWT authentication.

[![tests](https://github.com/Jpeg-create/nullvault/actions/workflows/tests.yml/badge.svg)](https://github.com/Jpeg-create/nullvault/actions/workflows/tests.yml)
![Python](https://img.shields.io/badge/python-3.8+-blue.svg)
![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-green.svg)
![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)

## What is NullVault?

NullVault lets developers securely store, retrieve, and manage API keys and secrets through a REST API. Secrets are encrypted at rest using Fernet symmetric encryption. Every action is logged in an audit trail.

## Features

- **JWT Authentication** — register and login, every endpoint is protected
- **Encrypted Secrets** — secrets stored encrypted, never in plaintext
- **Audit Logging** — every read, write, and delete is recorded with timestamp
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
| POST | /secrets/ | Store a secret | Yes |
| GET | /secrets/ | List secret names | Yes |
| GET | /secrets/{name} | Retrieve decrypted secret | Yes |
| DELETE | /secrets/{name} | Delete a secret | Yes |
| GET | /audit/ | View audit log | Yes |
| GET | /health | Health check | No |

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

Visit **http://127.0.0.1:8000/docs** for the interactive API documentation.

## License

MIT

