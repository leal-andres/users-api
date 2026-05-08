# Infraestructura GCP — Users API

Proyecto: **`stefanini-495702`** | Region: **`us-central1`** | Cuenta: `andresle96@gmail.com`

---

## Recursos creados

### 1. APIs habilitadas
| API | Uso |
|---|---|
| `run.googleapis.com` | Cloud Run (deploy del servicio) |
| `cloudbuild.googleapis.com` | Pipeline CI/CD |
| `sqladmin.googleapis.com` | Cloud SQL Postgres |
| `secretmanager.googleapis.com` | Secrets (DB password, app key) |
| `artifactregistry.googleapis.com` | Container registry |
| `iam.googleapis.com` | Service accounts y bindings |

### 2. Cloud SQL — Postgres

| Atributo | Valor |
|---|---|
| Instance ID | `users-api-db` |
| Connection name | `stefanini-495702:us-central1:users-api-db` |
| Edition | `ENTERPRISE` |
| Tier | `db-f1-micro` (shared-core, ~1 vCPU, 0.6 GB RAM) |
| Engine | Postgres 16 |
| Storage | 10 GB SSD, sin auto-increase |
| Region/Zone | `us-central1-a` (single zone, sin HA) |
| Backup | Deshabilitado |
| Public IP | `35.222.231.62` (en `users-api` AR; auth Proxy + IAM) |
| DB | `users_api` (creada y migrada) |
| User app | `postgres` (password en Secret Manager) |

**Costo estimado:** ~$8-10/mes.

### 3. Artifact Registry

| Atributo | Valor |
|---|---|
| Repo | `users-api` |
| Format | Docker |
| Region | `us-central1` |
| Path | `us-central1-docker.pkg.dev/stefanini-495702/users-api/users-api` |

### 4. Service Account (runtime de Cloud Run)

| Atributo | Valor |
|---|---|
| Email | `users-api-runtime@stefanini-495702.iam.gserviceaccount.com` |
| Display name | Users API Cloud Run runtime |

**Roles asignados:**
- `roles/cloudsql.client` — conectar a Cloud SQL via Auth Proxy / Unix socket
- `roles/secretmanager.secretAccessor` — leer secrets en runtime
- `roles/logging.logWriter` — escribir a Cloud Logging

### 5. Cloud Build SA (default)

Email: `462007401636@cloudbuild.gserviceaccount.com`

**Roles agregados** (para CI/CD):
- `roles/run.admin` — desplegar Cloud Run
- `roles/iam.serviceAccountUser` — actuar como `users-api-runtime`
- `roles/artifactregistry.writer` — push de imagenes
- `roles/secretmanager.secretAccessor` — leer secrets en steps de migrate
- `roles/cloudsql.client` — para correr migraciones desde el step

### 6. Secret Manager

| Secret | Contenido | Versions |
|---|---|---|
| `database-url` | Connection string completa con Unix socket: `postgresql+asyncpg://postgres:<urlencoded-password>@/users_api?host=/cloudsql/stefanini-495702:us-central1:users-api-db` | 1 |
| `secret-key` | App secret aleatoria (48 bytes base64) | 1 |

**Acceso:** runtime SA + Cloud Build SA (`secretmanager.secretAccessor`).

### 7. Cloud Run service

| Atributo | Valor |
|---|---|
| Service name | `users-api` |
| Region | `us-central1` |
| Image | `us-central1-docker.pkg.dev/stefanini-495702/users-api/users-api:<sha>` |
| CPU | 1 vCPU |
| Memory | 512 MiB |
| Min instances | 0 (scale-to-zero) |
| **Max instances** | **2** (limite duro para evitar costos) |
| Concurrency | 80 req/instance |
| Timeout | 60s |
| Auth | `--allow-unauthenticated` (publico, requerido por el challenge) |
| Cloud SQL | `--add-cloudsql-instances=stefanini-495702:us-central1:users-api-db` (Unix socket) |
| Service account | `users-api-runtime@...` |
| Env vars | `ENVIRONMENT=production` |
| Secrets injected | `DATABASE_URL`, `SECRET_KEY` |

**URL del servicio:** `https://users-api-w7muf5urhq-uc.a.run.app`

Endpoints publicos:
- Swagger UI → https://users-api-w7muf5urhq-uc.a.run.app/docs
- ReDoc → https://users-api-w7muf5urhq-uc.a.run.app/redoc
- OpenAPI JSON → https://users-api-w7muf5urhq-uc.a.run.app/openapi.json
- Liveness → https://users-api-w7muf5urhq-uc.a.run.app/health/live
- Readiness → https://users-api-w7muf5urhq-uc.a.run.app/health/ready

---

## Comandos utiles

### Conectar a Cloud SQL desde local
```bash
# Descargar Cloud SQL Auth Proxy una vez:
curl -sSLo /tmp/cloud-sql-proxy https://storage.googleapis.com/cloud-sql-connectors/cloud-sql-proxy/v2.13.0/cloud-sql-proxy.darwin.arm64
chmod +x /tmp/cloud-sql-proxy

# Levantar proxy en :5434
/tmp/cloud-sql-proxy --port=5434 stefanini-495702:us-central1:users-api-db

# Connect (en otra terminal)
gcloud secrets versions access latest --secret=database-url --project=stefanini-495702
# Usar la password de ese URL para psql -h localhost -p 5434 -U postgres -d users_api
```

### Re-deploy
```bash
cd users-api
gcloud builds submit --config=cloudbuild.yaml --project=stefanini-495702
```

### Aplicar nuevas migraciones (Alembic)
```bash
# Levantar proxy
/tmp/cloud-sql-proxy --port=5434 stefanini-495702:us-central1:users-api-db &

# Construir DATABASE_URL local apuntando al proxy
DB_URL="postgresql+asyncpg://postgres:$(gcloud secrets versions access latest --secret=database-url | sed -E 's|.*postgres:||;s|@.*||')@localhost:5434/users_api"
DATABASE_URL="$DB_URL" .venv/bin/alembic upgrade head

# Matar proxy
pkill -f cloud-sql-proxy
```

### Ver logs
```bash
gcloud run services logs read users-api --region=us-central1 --project=stefanini-495702 --limit=50
```

### Inspeccionar instancia Cloud SQL
```bash
gcloud sql instances describe users-api-db --project=stefanini-495702
gcloud sql databases list --instance=users-api-db --project=stefanini-495702
```

### Rotar password de DB
```bash
NEW=$(openssl rand -base64 32 | tr -d '\n')
gcloud sql users set-password postgres --instance=users-api-db --password="$NEW" --project=stefanini-495702

# URL-encode y crear nueva version del secret
ENC=$(python -c "import urllib.parse,sys; print(urllib.parse.quote(sys.argv[1], safe=''))" "$NEW")
URL="postgresql+asyncpg://postgres:${ENC}@/users_api?host=/cloudsql/stefanini-495702:us-central1:users-api-db"
printf '%s' "$URL" | gcloud secrets versions add database-url --data-file=- --project=stefanini-495702

# Re-deploy para que Cloud Run tome la nueva version
gcloud run services update users-api --region=us-central1 --project=stefanini-495702
```

