# Users API

REST API para gestion de usuarios (CRUD) construida con FastAPI, desplegada en Google Cloud Run con Cloud SQL Postgres.

**API publica:** https://users-api-w7muf5urhq-uc.a.run.app

| Recurso | URL |
|---|---|
| Swagger UI | https://users-api-w7muf5urhq-uc.a.run.app/docs |
| ReDoc | https://users-api-w7muf5urhq-uc.a.run.app/redoc |
| OpenAPI spec | https://users-api-w7muf5urhq-uc.a.run.app/openapi.json |
| Health (liveness) | https://users-api-w7muf5urhq-uc.a.run.app/health/live |
| Health (readiness) | https://users-api-w7muf5urhq-uc.a.run.app/health/ready |

---

## Stack

| Capa | Tecnologia |
|---|---|
| Framework | FastAPI |
| Validation | Pydantic v2 + pydantic-settings |
| ORM | SQLAlchemy 2.0 async |
| DB driver | asyncpg |
| Migraciones | Alembic |
| DB | PostgreSQL 16 (local en Docker / Cloud SQL en prod) |
| Logging | structlog + structlog-gcp (JSON estructurado, correlation IDs) |
| Testing | pytest + pytest-asyncio + httpx AsyncClient |
| Lint/format | ruff |
| Type check | mypy strict |
| Package manager | uv |
| Container | python:3.12-slim multi-stage, non-root |
| CI/CD | Cloud Build → Artifact Registry → Cloud Run |
| Secrets | Secret Manager (DATABASE_URL, SECRET_KEY) |

---

## Endpoints

| Method | Path | Descripcion | Status codes |
|---|---|---|---|
| POST | `/users` | Crear usuario (`active=false` por default — requiere activar) | 201, 409, 422 |
| GET | `/users?limit=&offset=&active=` | Listar (paginado, filtro opcional `active=true\|false`) | 200 |
| GET | `/users/{id}` | Obtener por id | 200, 404 |
| PATCH | `/users/{id}` | Update parcial | 200, 404, 409, 422 |
| POST | `/users/{id}/activate` | Activar usuario (idempotente) | 200, 404 |
| POST | `/users/{id}/deactivate` | Desactivar usuario (idempotente) | 200, 404 |
| DELETE | `/users/{id}` | Borrar (fisico) | 204, 404 |
| GET | `/health/live` | Liveness probe | 200 |
| GET | `/health/ready` | Readiness probe (verifica DB) | 200, 503 |

Errores devuelven `application/problem+json` (RFC 7807).

### Ejemplo de request

```bash
curl -X POST https://users-api-w7muf5urhq-uc.a.run.app/users \
  -H "Content-Type: application/json" \
  -d '{
    "username": "ada.lovelace",
    "email": "ada@example.com",
    "first_name": "Ada",
    "last_name": "Lovelace",
    "role": "admin"
  }'
```

Respuesta (`201 Created`):
```json
{
  "id": "d809a7d2-57dd-42ca-9209-14ee4e7f800a",
  "username": "ada.lovelace",
  "email": "ada@example.com",
  "first_name": "Ada",
  "last_name": "Lovelace",
  "role": "admin",
  "active": false,
  "created_at": "2026-05-08T03:52:10.993195Z",
  "updated_at": "2026-05-08T03:52:10.993195Z"
}
```

Activar el usuario:

```bash
curl -X POST https://users-api-w7muf5urhq-uc.a.run.app/users/d809a7d2-57dd-42ca-9209-14ee4e7f800a/activate
```

Listar solo activos:

```bash
curl "https://users-api-w7muf5urhq-uc.a.run.app/users?active=true"
```

### Postman

Importar `postman/users-api.postman_collection.json`. La coleccion ya trae las variables `base_url` (apuntando a prod) y `user_id` (vacia, se popula al correr `Create user → happy path`).

Estructura: 1 carpeta por operacion, cada una con happy path + casos de error (404/409/422).

Para usar la API local, basta con cambiar el valor de `base_url` en las variables de la coleccion a `http://localhost:8080`.

---

## Estructura del proyecto

```
users-api/
├── src/
│   ├── core/            config, logging, exception handlers (RFC 7807)
│   ├── db/              DeclarativeBase + async engine/session factory
│   ├── users/           feature module: router, schemas, models, repository, service, exceptions, dependencies
│   ├── health/          liveness + readiness probes
│   └── main.py          app factory + middlewares (CORS, correlation IDs)
├── tests/
│   ├── unit/            service tests con repository mockeado (12)
│   ├── integration/     endpoint tests con DB real (14)
│   └── conftest.py      fixtures: pg engine, client con dependency_overrides
├── alembic/             migraciones (env.py async)
├── postman/             coleccion + environments
├── Dockerfile           multi-stage, non-root, slim
├── cloudbuild.yaml      build → test → push → deploy a Cloud Run
├── pyproject.toml       deps via uv, config de ruff/mypy/pytest
├── INFRA.md             documentacion de los recursos GCP creados
└── README.md            (este archivo)
```

Arquitectura por capas:
- **router** parsea HTTP, llama service. No conoce DB.
- **service** logica de negocio (validar duplicados, lanzar excepciones de dominio). No conoce HTTP.
- **repository** acceso a DB. Recibe `AsyncSession`. No conoce reglas de negocio.

Inyeccion via `Depends()` (chain: session → repo → service).

---

## Setup local

### Requisitos
- Python 3.12+
- [uv](https://github.com/astral-sh/uv) (package manager)
- Docker (para Postgres local)

### Pasos

1. **Postgres local** — levantar un Postgres 16 en `localhost:5433`:

```bash
docker run -d --name users-pg \
  -e POSTGRES_PASSWORD=changeme \
  -e POSTGRES_DB=users_api \
  -p 5433:5432 \
  postgres:16-alpine
```

2. **Variables de entorno** — copiar `.env.example` a `.env` y ajustar:

```bash
cp .env.example .env
# editar DATABASE_URL si cambiaste el password
```

3. **Instalar dependencias:**

```bash
uv sync
```

4. **Aplicar migraciones:**

```bash
.venv/bin/alembic upgrade head
```

5. **Correr la app:**

```bash
.venv/bin/uvicorn src.main:app --reload --port 8080
```

Abrir http://localhost:8080/docs.

---

## Testing

```bash
# todos
.venv/bin/pytest -v

# solo unit (rapidos, sin DB real)
.venv/bin/pytest tests/unit -v

# solo integration (necesita Postgres en localhost:5433)
.venv/bin/pytest tests/integration -v

# con coverage
.venv/bin/pytest --cov=src --cov-report=term-missing
```

Tests integration usan una DB separada `users_api_test` (creada al primer run con `Base.metadata.create_all`). Cada test trunca la tabla en teardown.

---

## Quality checks

```bash
.venv/bin/ruff check src tests       # lint
.venv/bin/ruff format --check src tests   # format
.venv/bin/mypy src                   # type check (strict)
```

---

## Deploy

### Manual

```bash
gcloud builds submit --config=cloudbuild.yaml --project=stefanini-495702
```

`cloudbuild.yaml` ejecuta:
1. **build** — Docker image multi-stage
2. **test** — pytest tests/unit (en Python 3.12-slim)
3. **push** — a Artifact Registry
4. **deploy** — Cloud Run con secrets de Secret Manager y Cloud SQL via Unix socket

### Trigger automatico desde GitHub
Conectar el repo en Cloud Build → Triggers → "Push a main" con el `cloudbuild.yaml` del repo.

---

## Infra

Ver [INFRA.md](INFRA.md) para detalles de:
- Recursos creados en GCP (Cloud SQL, Cloud Run, Secret Manager, IAM, Artifact Registry)
- Comandos de re-deploy y rotacion de secretos

---

## Decisiones de diseño

| Decision | Por que |
|---|---|
| FastAPI sobre Flask/Django REST | Native async + Pydantic v2 + OpenAPI auto-generado |
| SQLAlchemy 2.0 async sobre SQLModel | Mas maduro, mejor soporte de Alembic, control completo |
| Capas router/service/repository | Testabilidad (cada capa mockeable) y separacion de concerns |
| RFC 7807 sobre formato custom | Estandar reconocido, mejor para clientes de terceros |
| UUID sobre auto-increment id | No revela cardinalidad, seguro para exponer en URLs |
| `StrEnum` para `UserRole` | Type-safe en Python, valores lowercase en DB y JSON |
| `PATCH` sobre `PUT` para update | Update parcial es lo que pide el caso real (cambiar 1 campo) |
| Cloud Run sobre App Engine/GKE | Scale-to-zero, simple, costo $0 en idle |
| Secrets en Secret Manager | Rotacion + version pinning + IAM granular |
| Migraciones en step de Cloud Build (manual la primera vez) | Evita race conditions con multiples instances de Cloud Run |
