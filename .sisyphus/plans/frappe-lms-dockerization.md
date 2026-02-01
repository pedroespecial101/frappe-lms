# Frappe LMS Dockerization Work Plan

**Project**: Dockerize Frappe LMS for unRAID deployment  
**Target**: Docker Compose setup with local image build (no Docker Hub)  
**Status**: Ready for execution  
**Estimated Duration**: 90-120 minutes

---

## User Decisions (Locked In)

| Question | Answer | Impact |
|----------|--------|--------|
| Video assets location | `/mnt/m2cache/mathmo-videos:/app/videos` | Bind mount from unRAID host |
| Persistent data location | `/mnt/m2cache/appdata/frappe-lms` | unRAID persistent storage standard |
| Existing docker setup | Create unRAID-specific setup | Clean slate, ignore docker/ folder |
| Deployment method | Docker Compose plugin | Standard docker-compose.yml |
| Admin password | `narlicwes0` via env var | Set in .env file |

---

## Architecture Overview

### Container Stack
```
┌─────────────────────────────────────────┐
│         Docker Compose Stack            │
├─────────────────────────────────────────┤
│  lms-app (Frappe + LMS)                 │
│    - Web server (port 9001)             │
│    - SocketIO (port 9000)               │
│    - Worker (background jobs)           │
│    - Scheduler (cron tasks)             │
├─────────────────────────────────────────┤
│  lms-db (MariaDB 10.8)                  │
│    - utf8mb4 charset                    │
├─────────────────────────────────────────┤
│  lms-redis (Redis Alpine)               │
│    - DB 0: cache (no persistence)       │
│    - DB 1: queue (AOF persistence)      │
│    - DB 2: socketio (no persistence)    │
└─────────────────────────────────────────┘
```

### Volume Strategy
```
unRAID Persistent Storage (Bind Mounts):
  /mnt/m2cache/appdata/frappe-lms/sites    → /home/frappe/frappe-bench/sites
  /mnt/m2cache/appdata/frappe-lms/db       → /var/lib/mysql
  /mnt/m2cache/appdata/frappe-lms/redis    → /data (AOF persistence for queue)
  /mnt/m2cache/appdata/frappe-lms/logs     → /home/frappe/frappe-bench/logs

Read-Only Mounts:
  /mnt/m2cache/mathmo-videos               → /app/videos (read-only)
```

---

## Deliverables

### 1. Dockerfile (Multi-Stage Build)
**Path**: `/Users/petetreadaway/Projects/frappe-lms/Dockerfile.unraid`  
**Max Lines**: 150  
**Stages**: 3 (frontend-build, python-deps, runtime)

**Stage 1: frontend-build**
- Base: `node:18-alpine`
- Build LMS frontend assets
- Output: `/frontend/dist`

**Stage 2: python-deps**
- Base: `python:3.11-slim`
- Install system dependencies (wkhtmltopdf, fonts, etc.)
- Create frappe user
- Install bench CLI
- Install Frappe Framework (version 15)
- Install LMS app from local source

**Stage 3: runtime**
- Copy bench workspace from python-deps
- Copy frontend assets from frontend-build
- Configure entrypoint
- Expose ports 9000, 9001

**Guardrails**:
- MUST NOT exceed 150 lines
- MUST use `.dockerignore` to exclude venv/, node_modules/, __pycache__/
- MUST NOT store secrets in image
- MUST install exact Frappe v15 (from requirements.txt)
- MUST create frappe user (non-root)

### 2. docker-compose.yml
**Path**: `/Users/petetreadaway/Projects/frappe-lms/docker-compose.unraid.yml`  
**Services**: 3 (lms-app, lms-db, lms-redis)

**Service: lms-db**
```yaml
- Image: mariadb:10.8
- Environment: MYSQL_ROOT_PASSWORD=${MYSQL_ROOT_PASSWORD}
- Command: utf8mb4 charset, skip-innodb-read-only-compressed
- Volume: /mnt/m2cache/appdata/frappe-lms/db:/var/lib/mysql
- Health check: mysqladmin ping every 10s
```

**Service: lms-redis**
```yaml
- Image: redis:alpine
- Command: redis-server --appendonly yes --appendfsync everysec
- Volume: /mnt/m2cache/appdata/frappe-lms/redis:/data
- Health check: redis-cli PING every 10s
```

**Service: lms-app**
```yaml
- Build: context=., dockerfile=Dockerfile.unraid
- Depends on: lms-db (healthy), lms-redis (healthy)
- Ports: 9000:9000, 9001:9001
- Volumes: 
    - /mnt/m2cache/appdata/frappe-lms/sites:/home/frappe/frappe-bench/sites
    - /mnt/m2cache/appdata/frappe-lms/logs:/home/frappe/frappe-bench/logs
    - /mnt/m2cache/mathmo-videos:/app/videos:ro
- Environment: DB_HOST, REDIS_CACHE, REDIS_QUEUE, ADMIN_PASSWORD
- Health check: curl /api/method/frappe.ping every 30s
```

**Guardrails**:
- MUST use dependency conditions (service_healthy)
- MUST NOT hardcode secrets (use ${VARS})
- MUST include health checks for ALL services
- MUST expose exact ports (9000, 9001)

### 3. Entrypoint Script
**Path**: `/Users/petetreadaway/Projects/frappe-lms/docker/entrypoint.sh`  
**Max Lines**: 100  
**Must Be**: Idempotent (run multiple times = same result)

**Logic Flow**:
```bash
1. Wait for MariaDB ready (mysqladmin ping, max 60s)
2. Wait for Redis ready (redis-cli PING, max 30s)
3. If site doesn't exist:
     - bench new-site lms.localhost
     - bench install-app lms
     - Set admin password
4. If site exists:
     - bench migrate (idempotent)
5. Start services:
     - bench serve (web)
     - node socketio.js (background)
     - bench worker (background)
     - bench schedule (background)
```

**Guardrails**:
- MUST be idempotent (no "already exists" failures)
- MUST exit with status 0 on success
- MUST log each step to stdout
- MUST handle SIGTERM gracefully (stop all services)
- MUST NOT use `bench start` (doesn't work in container)

### 4. Environment File Template
**Path**: `/Users/petetreadaway/Projects/frappe-lms/.env.unraid.example`  

**Required Variables**:
```
MYSQL_ROOT_PASSWORD=frappe123
ADMIN_PASSWORD=narlicwes0
DB_HOST=lms-db
REDIS_CACHE=redis://lms-redis:6379/0
REDIS_QUEUE=redis://lms-redis:6379/1
REDIS_SOCKETIO=redis://lms-redis:6379/2
SITE_NAME=lms.localhost
```

### 5. .dockerignore
**Path**: `/Users/petetreadaway/Projects/frappe-lms/.dockerignore`  

**Excluded Patterns**:
```
venv/
env/
node_modules/
__pycache__/
*.pyc
.git/
.github/
.vscode/
*.log
*.pid
.DS_Store
/lms-bench/
/sites/
```

### 6. Deployment README
**Path**: `/Users/petetreadaway/Projects/frappe-lms/README-UNRAID.md`  

**Sections**:
1. Prerequisites (Docker, Docker Compose on unRAID)
2. Quick Start (4 commands to running system)
3. Environment Variables
4. Volume Management
5. Accessing the System
6. Running Import Scripts
7. Troubleshooting
8. Backup/Restore
9. Updating

**Max Length**: 300 lines

---

## Execution Tasks

### Phase 1: Research (10 min)
- [x] **Task 1.1**: Launch librarian to fetch Frappe official Docker patterns
  - Query: "Frappe Framework Docker initialization and bench setup patterns"
  - Library ID: `/frappe/frappe`
  - Expected: Dockerfile reference, entrypoint patterns, bench commands

### Phase 2: Dockerfile Creation (25 min)
- [x] **Task 2.1**: Create `.dockerignore`
  - Exclude: venv/, node_modules/, __pycache__/, .git/, lms-bench/
  - Verify: `docker build` context < 100MB

- [x] **Task 2.2**: Write multi-stage Dockerfile
  - Stage 1: Build frontend (Node 18 Alpine)
  - Stage 2: Install Python deps + Frappe + LMS
  - Stage 3: Runtime with entrypoint
  - Verify: `docker build -t frappe-lms:local -f Dockerfile.unraid .` succeeds

- [x] **Task 2.3**: Test build caching
  - Run build twice
  - Verify: "CACHED" appears for unchanged layers

### Phase 3: Docker Compose Setup (20 min)
- [x] **Task 3.1**: Write `docker-compose.unraid.yml`
  - Define 3 services with health checks
  - Configure volumes and networks
  - Set dependency order

- [x] **Task 3.2**: Create `.env.unraid.example`
  - List all required variables
  - Document defaults

- [x] **Task 3.3**: Validate Compose file
  - Run: `docker-compose -f docker-compose.unraid.yml config`
  - Verify: No validation errors

### Phase 4: Entrypoint Script (20 min)
- [x] **Task 4.1**: Write `docker/entrypoint.sh`
  - Implement wait-for-services logic
  - Implement idempotent site initialization
  - Implement service startup (non-daemon mode)

- [x] **Task 4.2**: Make executable
  - Run: `chmod +x docker/entrypoint.sh`

- [ ] **Task 4.3**: Test idempotency logic
  - Mock scenario: site already exists
  - Verify: Script doesn't fail, proceeds to migrate

### Phase 5: Integration Testing (30 min)
- [ ] **Task 5.1**: First boot test
  - Run: `docker-compose -f docker-compose.unraid.yml up -d`
  - Wait: 2 minutes for initialization
  - Verify: All containers running

- [ ] **Task 5.2**: Health check verification
  - Check: `docker inspect lms-app --format='{{.State.Health.Status}}'`
  - Expected: "healthy" within 3 minutes

- [ ] **Task 5.3**: Service accessibility
  - Test: `curl http://localhost:9001/api/method/frappe.ping`
  - Expected: `{"message": "pong"}`
  - Test: `curl http://localhost:9001`
  - Expected: HTTP 200

- [ ] **Task 5.4**: Database verification
  - Run: `docker exec lms-db mysql -uroot -p$MYSQL_ROOT_PASSWORD -e "SHOW DATABASES;"`
  - Verify: Site database exists (starts with underscore)

- [ ] **Task 5.5**: Redis verification
  - Run: `docker exec lms-redis redis-cli -n 1 PING`
  - Expected: "PONG"

- [ ] **Task 5.6**: Site login test
  - Open: http://localhost:9001
  - Login: Administrator / narlicwes0
  - Verify: Dashboard loads

- [ ] **Task 5.7**: Video mount verification
  - Run: `docker exec lms-app ls -la /app/videos`
  - Verify: Files visible from host mount

### Phase 6: Persistence Testing (15 min)
- [ ] **Task 6.1**: Stop containers
  - Run: `docker-compose -f docker-compose.unraid.yml down`

- [ ] **Task 6.2**: Verify volumes exist
  - Run: `docker volume ls | grep lms`
  - Expected: 3 volumes (sites, db, redis)

- [ ] **Task 6.3**: Restart and verify data
  - Run: `docker-compose -f docker-compose.unraid.yml up -d`
  - Wait: 1 minute
  - Login: Administrator / narlicwes0
  - Verify: Dashboard loads (data persisted)

### Phase 7: Documentation (20 min)
- [x] **Task 7.1**: Write README-UNRAID.md
  - Quick start section
  - Environment variable reference
  - Troubleshooting common issues

- [x] **Task 7.2**: Add deployment checklist
  - Pre-deployment steps
  - Post-deployment verification

- [x] **Task 7.3**: Document import script usage
  - How to run: `docker exec lms-app bench --site lms.localhost execute lms.scripts.import_gcse_course.run_import`

---

## Acceptance Criteria (Executable)

### Build Phase
```bash
# Dockerfile builds successfully
docker build -t frappe-lms:local -f Dockerfile.unraid .
echo $? # Must be 0

# Image size reasonable
docker images frappe-lms:local --format "{{.Size}}"
# Should be < 2GB

# Multi-stage caching works
docker build -t frappe-lms:local -f Dockerfile.unraid . 2>&1 | grep -c "CACHED"
# Should be > 5 (at least 5 cached layers)
```

### Compose Validation
```bash
# Compose file validates
docker-compose -f docker-compose.unraid.yml config > /dev/null
echo $? # Must be 0

# Services start in order
docker-compose -f docker-compose.unraid.yml up -d
sleep 60
docker-compose -f docker-compose.unraid.yml ps --format json | jq -r '.State' | sort -u
# Should output only: running
```

### Service Health
```bash
# MariaDB healthy
docker inspect lms-db --format='{{.State.Health.Status}}'
# Output: healthy

# Redis healthy
docker inspect lms-redis --format='{{.State.Health.Status}}'
# Output: healthy

# Frappe app healthy
docker inspect lms-app --format='{{.State.Health.Status}}'
# Output: healthy (within 3 min)
```

### Functionality
```bash
# Frappe API responds
curl -f http://localhost:9001/api/method/frappe.ping
# Output: {"message":"pong"}

# SocketIO responds
curl -f http://localhost:9000/socket.io/ 2>&1 | grep -q "Missing"
# Exit code: 0 (proves socketio is running)

# Site accessible
curl -sI http://localhost:9001 | grep "HTTP" | grep -q "200"
# Exit code: 0

# Static assets serve
curl -f http://localhost:9001/assets/frappe/css/frappe-web.css > /dev/null
# Exit code: 0
```

### Data Persistence
```bash
# Stop and restart
docker-compose -f docker-compose.unraid.yml down
docker volume ls | grep -c "lms-"
# Output: 3 (three volumes exist)

docker-compose -f docker-compose.unraid.yml up -d
sleep 60

# Data survived
docker exec lms-db mysql -uroot -pfrappe123 -e "SHOW DATABASES LIKE '_%%';" | wc -l
# Output: > 1 (site database exists)
```

### Video Assets
```bash
# Mount visible in container
docker exec lms-app ls /app/videos | wc -l
# Output: > 0 (files present)

# Mount is read-only
docker exec lms-app touch /app/videos/test.txt 2>&1 | grep -q "Read-only"
# Exit code: 0
```

---

## Guardrails & Constraints

### MUST DO
- ✅ Follow Frappe official Docker initialization patterns (from librarian research)
- ✅ Use exact Python/Node versions from requirements
- ✅ Implement health checks for ALL services
- ✅ Make entrypoint idempotent (run twice = no errors)
- ✅ Use non-root user (frappe) in container
- ✅ Log all steps to stdout (Docker logs)
- ✅ Handle SIGTERM gracefully
- ✅ Document every environment variable
- ✅ Test on clean Docker environment (no cached data)

### MUST NOT DO
- ❌ Modify LMS source code (lms/ directory)
- ❌ Modify import scripts
- ❌ Add nginx/reverse proxy (out of scope)
- ❌ Add SSL/TLS (out of scope)
- ❌ Add monitoring tools (Prometheus, Grafana)
- ❌ Add backup automation (unRAID handles this)
- ❌ Add CI/CD pipelines
- ❌ Push image to Docker Hub (local build only)
- ❌ Optimize for multi-site (single site: lms.localhost)
- ❌ Store secrets in Dockerfile or compose file

### File Size Limits
- `Dockerfile.unraid`: Max 150 lines
- `entrypoint.sh`: Max 100 lines
- `docker-compose.unraid.yml`: Max 150 lines
- `README-UNRAID.md`: Max 300 lines
- `.dockerignore`: Max 50 lines
- `.env.unraid.example`: Max 30 lines

### Performance Targets
- First boot: Complete within 5 minutes
- Subsequent boots: Healthy within 90 seconds
- API response: < 2 seconds for /api/method/frappe.ping
- Docker image: < 2GB compressed

---

## Risk Mitigation

### Risk: Symlink Asset Serving Breaks
**Mitigation**: Ensure apps/ and sites/ are in same volume context
**Test**: Verify `/assets/lms/` serves files after build

### Risk: Redis Queue Data Loss
**Mitigation**: Enable AOF persistence for Redis database 1
**Test**: Stop container, verify appendonly.aof exists

### Risk: First-Run Race Condition
**Mitigation**: Use depends_on with service_healthy condition
**Test**: Check logs show MariaDB ready before bench commands

### Risk: Admin Password Visible
**Mitigation**: Use .env file (not committed), document in README
**Test**: Verify .env in .gitignore

### Risk: Port Conflicts on unRAID
**Mitigation**: Document ports clearly, support override via env vars
**Test**: Document in README how to change ports

---

## Execution Order

```
1. Research (librarian) → Dockerfile patterns
2. Create .dockerignore → Optimize build context
3. Write Dockerfile.unraid → Multi-stage build
4. Write docker-compose.unraid.yml → Service definitions
5. Write .env.unraid.example → Configuration template
6. Write docker/entrypoint.sh → Initialization logic
7. Build image → Test Dockerfile
8. Start stack → Test docker-compose
9. Run acceptance tests → Verify all functionality
10. Write README-UNRAID.md → Document deployment
```

**Critical Path**: Research → Dockerfile → Entrypoint → Testing  
**Parallel Work**: Can write .dockerignore + .env while researching

---

## Success Criteria

This plan is **COMPLETE** when:

1. ✅ All 6 deliverable files exist and pass validation
2. ✅ All 32 acceptance criteria pass (exit code 0)
3. ✅ Fresh `docker-compose up` reaches healthy state < 5 min
4. ✅ User can login with Administrator / narlicwes0
5. ✅ LMS accessible at http://localhost:9001/lms
6. ✅ Videos accessible from /app/videos mount
7. ✅ Import script runnable: `docker exec lms-app bench execute ...`
8. ✅ Data persists after `docker-compose down && up`
9. ✅ README documents all commands for unRAID deployment
10. ✅ No modifications to lms/ source code

**Definition of Done**: User can copy docker-compose.unraid.yml to unRAID, run `docker-compose up -d`, and have working LMS within 5 minutes with zero manual intervention.

---

## Estimated Timeline

| Phase | Duration | Dependencies |
|-------|----------|--------------|
| Research | 10 min | None |
| Dockerfile | 25 min | Research complete |
| Docker Compose | 20 min | Dockerfile complete |
| Entrypoint | 20 min | Dockerfile complete |
| Integration Testing | 30 min | All files complete |
| Persistence Testing | 15 min | Integration tests pass |
| Documentation | 20 min | All tests pass |
| **TOTAL** | **140 min** | |

**Confidence Level**: 90% (video mount is only unknown, but path confirmed by user)
