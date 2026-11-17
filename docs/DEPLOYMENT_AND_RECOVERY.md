# Project Caspian: Cloud Deployment & Recovery Guide

## 1. Overview
Project Caspian Research Communications Agent is designed to operate continuously in the cloud, uncoupling operations from the user's local machine. This guarantees uninterrupted delivery of daily AI intelligence briefings, scheduled post publishing to X, and on-demand Telegram management.

---

## 2. Deployment Architecture

```text
┌────────────────────────────────────────────────────────┐
│ Cloud Host (VPS, AWS EC2, GCP Compute, Railway)        │
│                                                        │
│  ┌──────────────────────────────────────────────────┐  │
│  │ Docker Container: caspian-agent                  │  │
│  │                                                  │  │
│  │  ┌──────────────────────┐ ┌────────────────────┐ │  │
│  │  │ Telegram Bot Service │ │ Background Worker  │ │  │
│  │  │ (Long Polling)       │ │ (Scheduler & Sweeps│ │  │
│  │  └──────────┬───────────┘ └─────────┬──────────┘ │  │
│  │             │                       │            │  │
│  │             ▼                       ▼            │  │
│  │      ┌────────────────────────────────────┐      │  │
│  │      │ Orchestrator / Skill Router        │      │  │
│  │      └─────────────────┬──────────────────┘      │  │
│  │                        ▼                         │  │
│  │      ┌────────────────────────────────────┐      │  │
│  │      │ SQLite Connection (WAL Mode)       │      │  │
│  │      └─────────────────┬──────────────────┘      │  │
│  └────────────────────────┼─────────────────────────┘  │
│                           │                            │
│  Persistent Volumes       ▼                            │
│  ├── ./data       --> /app/data       (caspian.db)     │
│  ├── ./documents  --> /app/documents  (PDF & DOCX)     │
│  └── ./logs       --> /app/logs       (Audit logs)     │
└────────────────────────────────────────────────────────┘
```

---

## 3. Production Quickstart

### 3.1 Prerequisites
- Docker and Docker Compose installed on host (`docker compose version >= 2.20`).
- Configured `.env` file containing valid credentials.

### 3.2 Environment Setup
Create a production `.env` file outside version control:

```bash
# Gemini LLM API
GEMINI_API_KEY="your-gemini-api-key"
GEMINI_MODEL="gemini-2.5-flash"

# Telegram Bot
TELEGRAM_BOT_TOKEN="your-bot-token"
TELEGRAM_AUTHORIZED_USER_ID="your-numeric-telegram-id"

# X (Twitter) API
X_API_KEY="your-x-api-key"
X_API_SECRET="your-x-api-secret"
X_ACCESS_TOKEN="your-x-access-token"
X_ACCESS_TOKEN_SECRET="your-x-access-token-secret"
X_DRY_RUN_MODE="false"

# Production Storage
DATABASE_PATH="/app/data/caspian.db"
LOG_LEVEL="INFO"
```

### 3.3 Launch Services
```bash
# Build and launch container in detached background mode
docker compose up -d --build

# Monitor live operational logs
docker compose logs -f caspian-agent
```

---

## 4. Health Monitoring & Verification

### 4.1 Automated Healthcheck
The container runs an automated healthcheck every 60 seconds (`scripts/healthcheck.py`):
- Pings SQLite connection to ensure read/write responsiveness.
- Inspects background worker liveness heartbeat in `system_settings`.
- Verifies that heartbeat is under 10 minutes old.

Check container health status:
```bash
docker inspect --format='{{json .State.Health}}' caspian-agent | jq
```

### 4.2 Application Status via Telegram
From your private Telegram chat, send `/status` to review:
- LLM connectivity.
- Database state and active connections.
- Registered skills and active tool counts.
- Background worker heartbeat.

---

## 5. Storage Persistence & Backups

### 5.1 Volume Structure
- `/app/data`: Contains the primary SQLite database (`caspian.db`), write-ahead log (`caspian.db-wal`), and shared memory (`caspian.db-shm`).
- `/app/documents`: Contains all generated research summaries, reports, and briefings exported as monochrome PDFs and DOCXs.
- `/app/logs`: Audit logs formatted as JSON with redacted secrets.

### 5.2 Safe SQLite Online Backups
Because SQLite runs in WAL mode (`PRAGMA journal_mode=WAL`), you can create safe hot backups without shutting down the agent:

```bash
# Execute safe SQLite online backup command
docker exec caspian-agent sqlite3 /app/data/caspian.db ".backup '/app/data/backup_$(date +%Y%m%d_%H%M%S).db'"
```

---

## 6. Failure Recovery Procedures

### 6.1 Container Crash or Node Restart
- The container is configured with `restart: unless-stopped`.
- When Docker restarts or the VM reboots, the agent automatically initializes database connections, starts the background scheduler thread, and connects to Telegram long polling.
- Double-publishing prevention is guaranteed across restarts by the database unique constraint on `(platform, content_hash)`.

### 6.2 SQLite WAL Recovery
If an ungraceful host shutdown occurs while WAL transactions were pending:
1. Stop the container: `docker compose down`
2. Run integrity check:
   ```bash
   sqlite3 data/caspian.db "PRAGMA integrity_check;"
   ```
3. Restart container: `docker compose up -d`
SQLite automatically applies and replays the WAL file on initialization.

### 6.3 Credential Rotation
If any API keys (Gemini, Telegram, X) need rotation:
1. Update `.env` with new credentials.
2. Restart the container:
   ```bash
   docker compose restart caspian-agent
   ```
Secrets are never written to disk, committed to Git, or exposed in logs.
