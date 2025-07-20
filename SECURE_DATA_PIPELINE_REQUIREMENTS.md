# Secure & Monitored Data-Pipeline – Minimum-Viable Implementation

---

## 1 Scope & Guiding Principles

- Deliver an end-to-end demonstration of a secure data-pipeline that:
  1. Ingests CSV data, encrypts it, streams it through Apache Storm for anonymisation, stores it in Postgres, and exposes it via a REST API.
  2. Detects unauthorised data changes and surfaces integrity / quality alerts.
  3. Enforces Role-Based Access Control (RBAC) for CRUD and read-only actions.
  4. Exports rich Prometheus metrics and ready-made Grafana dashboards.
- Keep the footprint small and **do not modify anything under** `backend/src/{stream,batch,common}` – these are required by the research scripts.
- Re-implement the API layer (`backend/api`) and the React dashboard (`frontend/`) in a **clean, modular, minimal** fashion.
- Everything must run with `docker-compose up -d` on a vanilla machine.

<details>
<summary>Out-of-Scope (for this iteration)</summary>

- Multi-tenancy, SSO, advanced IAM back-ends.
- Production-grade monitoring hardening (e.g., TLS everywhere, AuthN for Grafana).  
 Guidelines will be documented but not fully scripted.
</details>

---

## 2 High-Level Architecture

```mermaid
graph TD
  subgraph Frontend
    A["React Dashboard"]
  end
  subgraph API Layer (FastAPI)
    B1[/Upload Endpoint/]
    B2[/Query Endpoints/]
    B3[/RBAC Middleware/]
    B-->DB[(Postgres)]
    B-->P1[(Prometheus /metrics)]
  end
  subgraph Processing
    C1["Kafka Topic"]
    C2["Storm Topology (existing src/stream/storm_processor.py)"]
  end
  subgraph Monitoring
    P[Prometheus]-->G[Grafana]
  end
  A-->B
  B1-->C1
  C2-->DB
  DB--metrics-->P
  B--metrics-->P
  C2--metrics-->P
```

### Docker-Compose Services

- `postgres` _•_ `zookeeper` _•_ `kafka` _•_ `storm-nimbus` _•_ `storm-supervisor`
- `backend-api` _•_ `frontend` _•_ `prometheus` _•_ `grafana`

---

## 3 Data-Flow & Security Controls

| Stage     | Security / Integrity                                      | Tooling                  |
| --------- | --------------------------------------------------------- | ------------------------ |
| _Ingest_  | TLS (API), record SHA-256                                 | FastAPI + `hashlib`      |
| _Stream_  | TLS (Kafka), AES-256-GCM encryption in payload            | Kafka Producer           |
| _Process_ | Anonymisation (k-anon / DP / Token), compliance rules     | Existing Storm processor |
| _Store_   | Postgres columns encrypted with `pgcrypto`                | Postgres                 |
| _Access_  | RBAC middleware, per-record hash validations on read/edit | FastAPI middleware       |
| _Monitor_ | Prometheus metrics, Great Expectations table tests        | Prometheus / GE          |

---

## 4 Database Schema (additions)

```
-- jobs
id uuid PK | filename | status | started_at | finished_at | submitted_by

-- records
id uuid PK | job_id FK | payload_json (encrypted bytea) | sha256 | created_at

-- record_versions
id | record_id FK | payload_json_encrypted | sha256 | version_num | edited_by | edited_at

-- roles
role_name PK – DataEngineer, DataAnalyst, SecurityAuditor

-- users
id PK | username | role_name FK  -- seeded with demo users

-- access_log
id | user | action | target_id | timestamp | outcome
```

---

## 5 RBAC Model (Backend Middleware)

| Role             | Allowed Actions                                                                   |
| ---------------- | --------------------------------------------------------------------------------- |
| Data Engineer    | Upload job, read/write any record, view metrics                                   |
| Data Analyst     | Read records, **propose** edits (creates new version, requires Engineer approval) |
| Security Auditor | Read records & versions, read `access_log`, read metrics                          |

Implementation: FastAPI `Depends(get_current_user)` obtains role from a demo header `x-role`; decorators from `fastapi-rbac` enforce rules. All access decisions written to `access_log`.

---

## 6 REST API Specification

Base URL: `/api/v1`

| Verb | Path                         | Auth       | Description                             |
| ---- | ---------------------------- | ---------- | --------------------------------------- |
| POST | /jobs/upload                 | Engineer   | multipart CSV upload → returns `job_id` |
| GET  | /jobs                        | any        | list jobs                               |
| GET  | /jobs/{job_id}/records       | any        | paginated anonymised records            |
| GET  | /records/{record_id}         | any        | single record (latest)                  |
| GET  | /records/{record_id}/history | Auditor    | all versions                            |
| PUT  | /records/{record_id}         | Engineer   | update record (new version)             |
| GET  | /metrics                     | Prometheus | `/metrics` exposition                   |
| GET  | /healthz                     | none       | liveness probe                          |

Errors follow RFC 7807 problem-details.

---

## 7 Backend Implementation Guidelines

```
backend/api/
├── deps.py               # auth helpers, AES utils, DB session
├── main.py               # FastAPI, CORS, Prometheus middleware
├── routes/
│   ├── jobs.py
│   ├── records.py
│   └── metrics.py
└── models/               # Pydantic schemas
```

- AES-256: `cryptography.fernet.Fernet`; master key loaded from Docker secret.
- Hashing: `sha256(json.dumps(record,sort_keys=True).encode())`.
- Prometheus: `prometheus-client` ASGI middleware + counters: `jobs_submitted_total`, `records_modified_total`, `record_integrity_failures_total`; histogram `processing_latency_seconds`.
- Great Expectations: daily cron job container runs suite, pushes to Prometheus Pushgateway.

---

## 8 Storm / Kafka Integration

- Preserve `storm_processor.py`.
- _Producer_ inside `jobs.py`:
  1. Accept CSV upload.
  2. Split into records, encrypt payload.
  3. Publish to topic `ingest.{job_id}` (TLS Kafka connection).
- Docker-Compose spins up Zookeeper, Kafka, Storm Nimbus, Storm Supervisor.

---

## 9 Frontend Dashboard (React + Vite + Tailwind)

Pages:

1. **Home / Upload** – role dropdown (`Analyst`, `Engineer`, `Auditor`), CSV drag-and-drop.
2. **Jobs** – list jobs, link to Records.
3. **Records** – DataGrid, search, filter, edit/history actions gated by role.
4. **Monitoring** – Grafana iframe, Prometheus status chips.

State Management: React-Query. Axios instance injects `x-role` header.

---

## 10 Monitoring Stack

- **Prometheus** scrape targets:
  - backend-api (`/metrics`)
  - storm-supervisor JMX exporter
  - Postgres exporter
- **Grafana** dashboards shipped as JSON in `/grafana/provisioning/dashboards`.
- **Alerts** (Prometheus rule examples):
  - `record_integrity_failures_total > 0` for 5 m ⇒ _breach_detected_
  - 95-th latency quantile > 2 s ⇒ _high_latency_

---

## 11 Docker-Compose Overview

Services:

- `postgres` ( bitnami/postgresql:15 )
- `zookeeper` ( confluentinc/cp-zookeeper:7 )
- `kafka` ( confluentinc/cp-kafka:7 )
- `storm-nimbus`, `storm-supervisor` ( storm:2.6 )
- `backend-api` ( python:3.10-slim, uvicorn, FastAPI )
- `frontend` ( node:18-alpine build → nginx:stable )
- `prometheus` ( prom/prometheus )
- `grafana` ( grafana/grafana )

Volumes: Postgres, Prometheus, Grafana data. Network: `pipeline-net`.

---

## 12 Non-Functional Requirements

- **Performance:** ingest ≥5 000 records/min on dev laptop.
- **Availability:** all containers healthy; correct `depends_on` startup.
- **Observability:** 100 % of API paths export latency metrics.
- **Security:** AES key rotation via Docker secret; Kafka & API served over TLS.
- **Code Quality:** Pylint ≥8.5/10, ESLint error-free; Black, Prettier enforced.

---

## 13 Deliverables

1. Updated source tree:
   - `backend/api/` (refactored)
   - `frontend/` (React dashboard)
   - `docker-compose.yml`, `prometheus.yml`, Grafana dashboards JSON
   - `docs/SECURE_PIPELINE_SETUP.md` (run & troubleshooting)
2. Demo video (≤5 min) showing upload, processing, RBAC enforcement, Grafana alert.
3. Root-level README quick-start.

---

## 14 Acceptance Criteria

- `docker-compose up -d --build` completes with all containers healthy.
- CSV upload flows end-to-end; records visible in dashboard.
- Role dropdown adjusts permissions instantly.
- Analyst edit blocked (403); Engineer edit succeeds; Auditor sees history.
- Tampering record in DB triggers integrity alert metric & Prometheus alert.
- Grafana shows live throughput & error panels.

---

> **Note:** This blueprint refactors the current codebase into a clear, minimal, end-to-end secure data-pipeline demo _without_ touching the research analysis components under `backend/src/`. Ensure future changes respect this boundary.
