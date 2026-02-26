## Marketing Automation Platform

Enterprise-grade marketing automation system built with **FastAPI + SQLAlchemy + Celery + PostgreSQL + React/TypeScript**.

### Architecture

- **API-first backend**: FastAPI app in `backend/` with modular routers for auth, campaigns, workflows, events, analytics, and realtime.
- **Database**: PostgreSQL with UUID primary keys, normalized schema via SQLAlchemy models in `backend/models.py` and Alembic migrations in `alembic/`.
- **Async & automation**: Celery workers (`backend/celery_app.py`, `backend/tasks.py`) with Redis broker handle email sending, workflow advancement, and delayed tasks.
- **Email abstraction**: `backend/email_providers.py` defines a pluggable provider interface (SES/SendGrid ready); default implementation logs to console in dev.
- **Frontend**: React + TypeScript SPA in `frontend/` (Vite) using JWT auth, a real-time dashboard, and API-only business logic.
- **Deployment**: Docker-compatible via `Dockerfile.backend` and `docker-compose.yml` (db, redis, backend, worker).

### Database Design

- **Users & Identity**
  - `users`: core identity with `email`, `hashed_password`, status.
  - `user_attributes`: JSONB per-user flexible attributes.
- **Campaigns & Workflows**
  - `campaigns`: logical campaigns.
  - `workflows`: data-driven workflow definitions tied to campaigns.
  - `workflow_nodes`: typed nodes (`start`, `email`, `delay`, `condition`, `end`) with JSONB `config`.
  - `workflow_edges`: directed edges with optional JSONB `condition` for branching.
- **Workflow Runtime**
  - `workflow_instances`: per-user workflow executions with status.
  - `workflow_steps`: stateful node execution records (pending/running/completed/failed).
- **Email System**
  - `email_templates`: HTML templates with subjects.
  - `email_sends`: individual email send attempts, linked to user, campaign, workflow, step, and provider id.
- **Event Tracking**
  - `events`: core event log for `sent`, `opened`, `clicked`, `bounced`, `unsubscribed`, referencing user/campaign/workflow/step/email_send plus JSONB `metadata`.
- **Segmentation & Lead Scoring**
  - `segments`: dynamic segments via JSONB `query` definition.
  - `lead_scores`: per-user score.
  - `lead_score_rules`: configurable JSONB rules + point weights.
- **Human Handoff (CRM-lite)**
  - `pipelines`: sales pipelines.
  - `pipeline_items`: leads in a pipeline with `status`, `owner`, and notes.
- **A/B Testing**
  - `ab_tests`: experiments and target metric.
  - `ab_variants`: variants with JSONB configuration and traffic split.
- **Auth & RBAC**
  - `roles`: `admin`, `marketing`, `sales`, `viewer`.
  - `user_roles`: many-to-many mapping.
- **Compliance & Audit**
  - `suppression_list`: unsubscribed/suppressed emails and reason.
  - `audit_logs`: structured audit trail with user, entity, and metadata.

All tables use **UUID primary keys** and `created_at`/`updated_at` timestamp fields.

### Workflow Execution Model

- Workflows are **fully data-driven**:
  - Nodes store type + JSONB configuration.
  - Edges define the execution graph with optional conditions.
- Runtime:
  - A `workflow_instance` is created per user entry.
  - The Celery task `advance_workflow_task` (`backend/tasks.py`) advances instances:
    - Finds the appropriate node (`start` for new instances).
    - Creates `workflow_steps` for each node execution.
    - Handles `delay` nodes by scheduling itself with an ETA.
    - Email nodes are wired to trigger `send_email_task`, which uses the configured provider.
- **Events** are written for key actions (e.g., email `sent`) to `events` and drive analytics, lead scoring, and real-time dashboards.

### Real-time Dashboard

- Backend exposes an **SSE endpoint** at `/api/realtime/events` that:
  - Polls recent `events` ordered by `created_at`.
  - Streams them as server-sent events (`text/event-stream`).
- Frontend dashboard (`frontend/src/dashboard/Dashboard.tsx`):
  - Pulls funnel metrics from `/api/analytics/funnel`.
  - Opens an `EventSource` to `/api/realtime/events` and displays a live event feed.

### Auth & Permissions

- JWT-based auth with `/api/auth/token` issuing access tokens:
  - Uses OAuth2 password flow and `python-jose`.
  - Tokens embed user id in `sub`.
- Role-based authorization via `roles` / `user_roles` and the `require_roles` dependency in `backend/auth.py`:
  - Example: campaign creation is limited to `admin` and `marketing`.

### Running the System

1. **Start infrastructure and backend**
   - Use the provided scripts:
     - Windows: `.\scripts\start-dev.ps1`
     - Linux/Mac: `./scripts/start-dev.sh`
   - These scripts handle starting PostgreSQL, Redis, the FastAPI backend, and Celery workers.
2. **Run migrations**
   - Inside the backend container or host:
     - `alembic upgrade head`
3. **Seed initial data**
   - `python -m backend.seed`
   - Creates roles, an admin user (`admin@example.com` / `admin123`), and an example campaign.
4. **Access the Application**
   - Backend API Docs: `http://localhost:8000/docs`
   - Frontend Dashboard: `http://localhost:5173`

### Scaling Considerations

- **Backend**
  - Stateless FastAPI instances behind a load balancer.
  - Shared PostgreSQL and Redis.
  - Celery workers horizontally scalable; use queues per concern (email, workflows, scoring).
- **Database**
  - Normalize core entities; JSONB only for flexible configs and metadata.
  - Use indexes on high-traffic columns (e.g. `events.type`, timestamps).
  - Consider read replicas and partitioning for large `events` tables.
- **Real-time**
  - Replace simple polling-based SSE with Redis Pub/Sub or dedicated streaming services for high volume.
- **Email**
  - Swap `ConsoleEmailProvider` with SES/SendGrid provider, using provider-specific webhooks to feed `events`.
- **Security & Compliance**
  - Tighten CORS, secrets management (ENV/secret store), and TLS termination.
  - Extend suppression and consent tracking to integrate with provider-level suppressions.

