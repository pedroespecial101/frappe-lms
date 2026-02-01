# MASTER REFERENCE: Frappe Framework Docker Patterns (Jan 31, 2026)

## QUICK REFERENCE - Copy-Paste Ready Code

### 1. APPS.JSON FOR CUSTOM BUILDS
```json
[
  {
    "url": "https://github.com/frappe/frappe",
    "branch": "version-15"
  },
  {
    "url": "https://github.com/frappe/lms",
    "branch": "main"
  },
  {
    "url": "https://github.com/frappe/erpnext",
    "branch": "version-15"
  }
]
```

**Encode to base64**:
```bash
export APPS_JSON_BASE64=$(base64 -w 0 apps.json)
```

### 2. DOCKER BUILD COMMAND
```bash
docker build \
  --build-arg=FRAPPE_PATH=https://github.com/frappe/frappe \
  --build-arg=FRAPPE_BRANCH=version-15 \
  --build-arg=APPS_JSON_BASE64=$APPS_JSON_BASE64 \
  --tag=custom/lms:15 \
  --file=images/layered/Containerfile .
```

### 3. DOCKER COMPOSE GENERATION
```bash
docker compose --env-file .env \
    -f compose.yaml \
    -f overrides/compose.mariadb.yaml \
    -f overrides/compose.redis.yaml \
    -f overrides/compose.noproxy.yaml \
    config > docker-compose.yml
```

### 4. DOCKER COMPOSE UP
```bash
docker compose -p frappe -f docker-compose.yml up -d
```

### 5. SITE CREATION
```bash
docker compose -p frappe exec backend bench new-site lms.localhost \
  --mariadb-user-host-login-scope='172.%.%.%' \
  --db-root-password 123 \
  --admin-password admin \
  --install-app frappe \
  --install-app lms
```

### 6. MIGRATIONS
```bash
docker compose -p frappe exec backend bench --site lms.localhost migrate
```

---

## ENVIRONMENT FILE (.env)

```bash
# Core
FRAPPE_PATH=https://github.com/frappe/frappe
FRAPPE_BRANCH=version-15
ERPNEXT_VERSION=v15.0.0

# Security (NEVER commit these!)
DB_PASSWORD=your_secure_password_here
ADMIN_PASSWORD=narlicwes0

# Database
DB_HOST=db
DB_PORT=3306

# Redis
REDIS_CACHE=redis-cache:6379
REDIS_QUEUE=redis-queue:6379

# Site
FRAPPE_SITE_NAME_HEADER=lms.localhost

# Image
CUSTOM_IMAGE=custom
CUSTOM_TAG=15
PULL_POLICY=missing

# Ports
HTTP_PUBLISH_PORT=8080
PROXY_READ_TIMEOUT=120
CLIENT_MAX_BODY_SIZE=50m
```

---

## SERVICE ARCHITECTURE

### compose.yaml Base (7 Services)

```yaml
configurator:     # One-shot: writes common_site_config.json
  - runs: bash -c "bench set-config ..."
  - depends_on: [] (nothing)
  - restart: on-failure

backend:          # Web server
  - runs: gunicorn frappe.app:application
  - port: 8000
  - depends_on: configurator (service_completed_successfully)

frontend:         # Nginx proxy
  - runs: nginx-entrypoint.sh
  - port: 8080
  - depends_on: [backend, websocket]

websocket:        # Node Socket.IO
  - runs: node /home/frappe/frappe-bench/apps/frappe/socketio.js
  - port: 9000
  - depends_on: configurator

queue-short:      # Worker (short jobs)
  - runs: bench worker --queue short,default
  - depends_on: configurator

queue-long:       # Worker (long jobs)
  - runs: bench worker --queue long,default,short
  - depends_on: configurator

scheduler:        # Periodic tasks
  - runs: bench schedule
  - depends_on: configurator
```

### Overrides

**compose.mariadb.yaml**:
```yaml
db:
  image: mariadb:11.8
  environment:
    MYSQL_ROOT_PASSWORD: ${DB_PASSWORD}
    MARIADB_AUTO_UPGRADE: 1
  volumes:
    - db-data:/var/lib/mysql
```

**compose.redis.yaml**:
```yaml
redis-cache:
  image: redis:6.2-alpine
  restart: unless-stopped

redis-queue:
  image: redis:6.2-alpine
  restart: unless-stopped
  volumes:
    - redis-queue-data:/data
```

---

## VOLUME MOUNTS (Docker Compose)

```yaml
volumes:
  sites:              # /home/frappe/frappe-bench/sites
  db-data:            # /var/lib/mysql (MariaDB)
  redis-queue-data:   # /data (Redis queue persistence)

# In services:
backend:
  volumes:
    - sites:/home/frappe/frappe-bench/sites

db:
  volumes:
    - db-data:/var/lib/mysql

redis-queue:
  volumes:
    - redis-queue-data:/data
```

---

## DOCKERFILE PATTERN (Layered, Recommended)

```dockerfile
ARG FRAPPE_BRANCH=version-15

# Stage 1: Builder
FROM frappe/build:${FRAPPE_BRANCH} AS builder

ARG FRAPPE_BRANCH=version-15
ARG FRAPPE_PATH=https://github.com/frappe/frappe
ARG APPS_JSON_BASE64

USER root

RUN if [ -n "${APPS_JSON_BASE64}" ]; then \
    mkdir /opt/frappe && echo "${APPS_JSON_BASE64}" | base64 -d > /opt/frappe/apps.json; \
  fi

USER frappe

RUN export APP_INSTALL_ARGS="" && \
  if [ -n "${APPS_JSON_BASE64}" ]; then \
    export APP_INSTALL_ARGS="--apps_path=/opt/frappe/apps.json"; \
  fi && \
  bench init ${APP_INSTALL_ARGS} \
    --frappe-branch=${FRAPPE_BRANCH} \
    --frappe-path=${FRAPPE_PATH} \
    --no-procfile \
    --no-backups \
    --skip-redis-config-generation \
    --verbose \
    /home/frappe/frappe-bench && \
  cd /home/frappe/frappe-bench && \
  echo "{}" > sites/common_site_config.json && \
  find apps -mindepth 1 -path "*/.git" | xargs rm -fr

# Stage 2: Runtime
FROM frappe/base:${FRAPPE_BRANCH} AS backend

USER frappe

COPY --from=builder --chown=frappe:frappe /home/frappe/frappe-bench /home/frappe/frappe-bench

WORKDIR /home/frappe/frappe-bench

VOLUME [ \
  "/home/frappe/frappe-bench/sites", \
  "/home/frappe/frappe-bench/sites/assets", \
  "/home/frappe/frappe-bench/logs" \
]

CMD [ \
  "/home/frappe/frappe-bench/env/bin/gunicorn", \
  "--chdir=/home/frappe/frappe-bench/sites", \
  "--bind=0.0.0.0:8000", \
  "--threads=4", \
  "--workers=2", \
  "--worker-class=gthread", \
  "--worker-tmp-dir=/dev/shm", \
  "--timeout=120", \
  "--preload", \
  "frappe.app:application" \
]
```

---

## COMMON BENCH COMMANDS (In Container)

```bash
# Site operations
docker compose -p frappe exec backend bench new-site <sitename>
docker compose -p frappe exec backend bench --site <sitename> install-app <app>
docker compose -p frappe exec backend bench --site <sitename> migrate
docker compose -p frappe exec backend bench --site <sitename> backup

# Configuration
docker compose -p frappe exec backend bench set-config -g db_host db
docker compose -p frappe exec backend bench set-config -gp socketio_port 9000

# Database
docker compose -p frappe exec backend bench reset-perms --site <sitename>
docker compose -p frappe exec backend bench clear-cache

# Logs
docker compose -p frappe logs backend -f
docker compose -p frappe logs configurator --tail=50
```

---

## TROUBLESHOOTING COMMANDS

```bash
# Check service status
docker compose -p frappe ps

# View service logs
docker compose -p frappe logs backend -f
docker compose -p frappe logs configurator --tail=50

# Access container shell
docker compose -p frappe exec backend bash

# Check database connection
docker compose -p frappe exec backend mysql -h db -u root -p123 -e "SELECT 1"

# Check Redis connection
docker compose -p frappe exec backend redis-cli -h redis-cache ping

# Restart specific service
docker compose -p frappe restart backend

# Recreate specific service
docker compose -p frappe up -d --force-recreate backend

# Stop all containers
docker compose -p frappe down

# Remove all data (WARNING: destructive!)
docker compose -p frappe down -v
```

---

## ENVIRONMENT VARIABLE DEFAULTS

| Variable | Default | Notes |
|----------|---------|-------|
| BACKEND | 0.0.0.0:8000 | Nginx upstream |
| SOCKETIO | 0.0.0.0:9000 | Socket.IO upstream |
| DB_HOST | db | Service name |
| DB_PORT | 3306 | MariaDB port |
| REDIS_CACHE | redis-cache:6379 | Cache Redis |
| REDIS_QUEUE | redis-queue:6379 | Queue Redis |
| FRAPPE_SITE_NAME_HEADER | $host | Multi-tenant routing |
| HTTP_PUBLISH_PORT | 8080 | Nginx external port |
| PROXY_READ_TIMEOUT | 120 | Upstream timeout (s) |
| CLIENT_MAX_BODY_SIZE | 50m | Max upload size |

---

## IMPORTANT GOTCHAS

### 1. MariaDB Host Scope
**WRONG**: `--mariadb-user-host-login-scope='localhost'`
```
Reason: Docker assigns dynamic IPs, container restart changes IP
Result: Database connection fails after container restart
```

**CORRECT**: `--mariadb-user-host-login-scope='172.%.%.%'`
```
Reason: Wildcard matches Docker's IP range
Result: Connections work after restart
```

### 2. NEVER Use `bench start` in Containers
**WRONG**:
```dockerfile
RUN bench start  # or in CMD
```

**CORRECT**:
```yaml
backend:
  command: gunicorn --bind=0.0.0.0:8000 ...
websocket:
  command: node socketio.js
queue-short:
  command: bench worker --queue short,default
scheduler:
  command: bench schedule
```

### 3. Site Creation AFTER Container Start
**WRONG**:
```dockerfile
RUN bench new-site lms.localhost  # Database not running!
```

**CORRECT**:
```bash
docker compose exec backend bench new-site lms.localhost
```

### 4. Configuration Timing
1. Build: Image created with Frappe + LMS code
2. Init: configurator runs once, writes config
3. Runtime: Services read config from common_site_config.json

**NOT**: Writing config in Dockerfile or at build time

### 5. Volume Persistence
**Don't mount**: /home/frappe/frappe-bench (entire directory)
- Breaks migrations and updates

**DO mount**: 
- /home/frappe/frappe-bench/sites (site data)
- /var/lib/mysql (database)
- /data (redis persistence)

---

## VERSION REFERENCE (Frappe v15)

| Component | Version | Notes |
|-----------|---------|-------|
| Frappe | version-15 / v15.86.0 | Latest stable |
| Bench | v5.x | Package manager |
| Python | 3.11.6 | Production |
| Node | 20.19.2 | Production |
| Debian | bookworm-slim | Base image |
| MariaDB | 11.8 | Latest stable |
| Redis | 6.2-alpine | Proven stable |
| nginx | Latest | From Debian packages |

---

## OFFICIAL GITHUB PERMALINKS

All patterns sourced from official Frappe Docker repository:
- Repository: https://github.com/frappe/frappe_docker
- Version: v1.0.1 (Jan 19, 2026)
- Commit: 23593bfadb0ceb949961e2b26242b77029d2563b

**Key files**:
1. Layered Containerfile: images/layered/Containerfile
2. Compose: compose.yaml
3. Docs: docs/02-setup/02-build-setup.md (build) & docs/02-setup/03-start-setup.md (deployment)

---

## NEXT STEPS FOR FRAPPE LMS

1. **Create Containerfile** using layered pattern
2. **Create apps.json** with frappe, lms, custom apps
3. **Build image**: `docker build --build-arg=APPS_JSON_BASE64=$APPS_JSON_BASE64 ...`
4. **Generate compose**: Combine base + overrides (mariadb, redis, noproxy)
5. **Create .env**: Database password, admin password, site name
6. **Start containers**: `docker compose up -d`
7. **Create site**: `docker compose exec backend bench new-site lms.localhost ...`
8. **Verify**: Access http://localhost:8080, login, check Socket.IO, run migrations

---

**Research Completed**: Jan 31, 2026, 16:35 UTC
**Source**: Official Frappe Docker repository + Framework documentation
**Status**: Ready for implementation
