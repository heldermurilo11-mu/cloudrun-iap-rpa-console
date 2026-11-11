# Cloud Run IAP RPA Console

Serverless **Cloud Run RPA Operations Console** built with **FastAPI**, **Google Cloud Identity-Aware Proxy (IAP)**, **Cloud Firestore**, **Cloud Run Jobs**, **Cloud Scheduler**, and **Cloud Logging**, paired with a zero-build Vanilla JS Single-Page Application.

Designed around a strict **Read-Only ("Portão A")** operational observability perimeter: operators and administrators can inspect datapool queues, materialized KPIs, Cloud Run job metadata/executions, scheduler states, structured logs, and dual-sink audit trails without exposing any mutation surface.

---

## Architecture Overview

```
+-----------------------------------------------------------------------------+
|                    FRONTEND: Zero-Build Vanilla JS SPA                      |
|  [Overview] | [Datapools] | [Jobs] | [Schedulers] | [Logs] | [Audit Trail]  |
|   Strict CSP (default-src 'self')  |  Page Visibility API (15s polling)     |
+-----------------------------------------------------------------------------+
                                      | HTTPS / REST (GET only; 405 on writes)
+-----------------------------------------------------------------------------+
|                   BACKEND: FastAPI on Cloud Run (Python 3.11)               |
|  /api/me  |  /api/datapools  |  /api/jobs  |  /api/schedulers               |
|  /api/logs  |  /api/audit  |  /healthz                                      |
|  Security: ES256 IAP JWT Middleware + Allowlist Governance + CSP Headers    |
+-----------------------------------------------------------------------------+
        |                  |                    |                  |
+---------------+  +----------------+  +----------------+  +------------------+
|   Firestore   |  | Cloud Run Jobs |  | Cloud Scheduler|  |  Cloud Logging   |
| (Materialized |  |  (Read-Only    |  |  (Read-Only    |  | (Worker Logs +   |
|  Counters &   |  |   Metadata &   |  |   Cron State)  |  |  Authoritative   |
|  Audit Model) |  |  Executions)   |  |                |  |  Audit Sink)     |
+---------------+  +----------------+  +----------------+  +------------------+
```

### Core Capabilities
1. **Overview & Materialized KPIs (`/api/datapools/summary`)**: Live counters (`QUEUED`, `PROCESSING`, `DONE`, `FAILED`, `TIMEOUT`, `CANCELED`) and global success rate without full-collection document scans.
2. **Datapools Explorer (`/api/datapools/*`)**: Allowlist-gated queue inspection, status filtering, cursor pagination, search, and read-only JSON payload inspection.
3. **Cloud Run Jobs & Executions (`/api/jobs`, `/api/jobs/executions`)**: Catalog of approved worker jobs (CPU/memory/timeout/image metadata) and execution telemetry.
4. **Cloud Schedulers (`/api/schedulers`)**: Visibility into cron expressions, timezones, and operational states (`ENABLED`, `PAUSED`, `DISABLED`).
5. **Structured Logs (`/api/logs`)**: Filtered Cloud Logging viewer scoped to `cloud_run_job`, audit logs, and configured worker log streams (`BOT_LOG_NAMES`).
6. **Dual Audit Trail (`/api/audit`)**: Authoritative structured logging in Cloud Logging backed by a Firestore read-model (`audit_trail`).

---

## Security Model (Portão A — Read-Only Perimeter)

* **Cryptographic IAP JWT Verification (`ES256`)**: Validates `X-Goog-IAP-JWT-Assertion` signatures against Google's P-256 JWKS endpoint with in-memory caching, rate-limited key rotation refresh, strict `aud` matching (`strict_aud=True`), issuer verification (`https://cloud.google.com/iap`), token lifetime bounds, and 30s clock-skew tolerance.
* **Fail-Closed Defaults**:
  * `AUTH_MODE=local` is blocked with **HTTP 403** when `ENVIRONMENT=production`.
  * Missing or empty `IAP_EXPECTED_AUDIENCE` in `iap` mode fails closed with **HTTP 503**.
  * JWKS outages or malformed provider keys fail closed with **HTTP 503** without trusting expired keys.
  * Empty `IAP_ALLOWED_DOMAINS` or domain mismatch (strict post-`@` match) fails closed with **HTTP 403**.
  * Explicit role mapping via `IAP_ADMIN_EMAILS` (`admin` vs `operator`).
* **Strict Read-Only Surface**: All API routers expose only `GET` endpoints; `POST`, `PUT`, `DELETE`, and `PATCH` requests are automatically rejected with **HTTP 405 Method Not Allowed**.
* **Resource Allowlist Governance**: Every datapool prefix (`ALLOWED_DATAPOOL_PREFIXES`), Cloud Run job (`ALLOWED_JOBS`), and scheduler (`ALLOWED_SCHEDULERS`) is checked against explicit allowlists (HTTP 403 on unauthorized access).
* **Zero-CDN CSP & XSS Protection**: Enforces `Content-Security-Policy: default-src 'self'`, `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, and HTML escaping on all dynamic SPA renders.
* **Server-Side Aggregation / Materialized Counters**: Reads versioned counter documents (`counters_version == 1`) or Firestore server-side `.count()` aggregations, never streaming full collections for metrics.

---

## Local Setup & Running

### 1. Configure Environment
Copy `.env.example` to `.env` and adjust values as needed:
```bash
cp .env.example .env
```

Key environment variables (`.env.example`):
| Variable | Default | Description |
|---|---|---|
| `ENVIRONMENT` | `local` | Runtime environment (`local`, `staging`, `production`) |
| `AUTH_MODE` | `local` | `local` (dev bypass, blocked in production) or `iap` |
| `GCP_PROJECT_ID` | `your-gcp-project-id` | Target Google Cloud project ID |
| `GCP_REGION` | `us-central1` | Region for Cloud Run Jobs and Cloud Scheduler |
| `FIRESTORE_DATABASE` | `(default)` | Firestore database name |
| `IAP_EXPECTED_AUDIENCE` | `""` | IAP signed JWT audience (`/projects/.../services/...`) |
| `IAP_ALLOWED_DOMAINS` | `example.com` | Comma-separated allowed email domains |
| `IAP_ADMIN_EMAILS` | `admin@example.com` | Comma-separated admin emails for RBAC |
| `ALLOWED_DATAPOOL_PREFIXES` | `sample_queue_,datapools_staging` | Allowed Firestore datapool name prefixes |
| `ALLOWED_JOBS` | `sample-producer-job,sample-consumer-job` | Allowed Cloud Run job names |
| `ALLOWED_SCHEDULERS` | `cron-producer,cron-consumer` | Allowed Cloud Scheduler job names |
| `BOT_LOG_NAMES` | `rpa-bots-worker` | Comma-separated Cloud Logging worker log names |
| `EXECUTIONS_COLLECTION` | `executions` | Firestore collection for job execution telemetry |
| `DEFAULT_TIMEZONE` | `UTC` | Default scheduler timezone fallback |

### 2. Install Dependencies
```bash
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

### 3. Run the Synthetic Local Console (Zero GCP Credentials Required)
```bash
python scripts/local_synthetic_server.py
```
Open `http://127.0.0.1:8080` in your browser. While running, you can also execute the live verification and security smoke scripts:
```bash
python scripts/verify_live_server.py
python scripts/verify_security.py
python scripts/benchmark_latency.py
```

### 4. Seed Staging Firestore Data (Optional, Requires GCP Credentials)
```bash
python scripts/seed_staging_data.py
uvicorn orchestrator.server:app --host 0.0.0.0 --port 8080 --reload
```

---

## Running Tests

```bash
pytest -v
```

---

## Container Build & Cloud Run Deployment

```bash
# Build non-root container image
docker build -t us-central1-docker.pkg.dev/your-gcp-project-id/rpa-images/cloudrun-iap-rpa-console:latest .

# Deploy private Cloud Run service behind Internal Load Balancer + IAP
gcloud run deploy cloudrun-iap-rpa-console \
  --image us-central1-docker.pkg.dev/your-gcp-project-id/rpa-images/cloudrun-iap-rpa-console:latest \
  --region us-central1 \
  --ingress internal-and-cloud-load-balancing \
  --set-env-vars ENVIRONMENT=production,AUTH_MODE=iap \
  --cpu 1 \
  --memory 512Mi \
  --min-instances 0 \
  --max-instances 2
```
