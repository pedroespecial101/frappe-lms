# Decisions - Frappe LMS Dockerization

## Session: ses_3eb324a00ffejrWUFevRPg1686
**Started**: 2026-01-31T16:34:07.713Z

---

## User Locked Decisions
- Video mount: `/mnt/m2cache/mathmo-videos:/app/videos` (read-only)
- Persistent data: `/mnt/m2cache/appdata/frappe-lms/` (sites, db, redis, logs)
- Admin password: `narlicwes0`
- Deployment: Docker Compose on unRAID
- Approach: Clean unRAID-specific setup

---


---

## Docker Architecture Decision (Jan 31, 2026)

### Build Strategy Decision: LAYERED MULTI-STAGE
**Recommendation**: Use `layered` approach (Frappe Docker's recommended pattern)

**Rationale**:
1. **Reuses Official Images**: Faster builds, automatic updates with frappe/build and frappe/base
2. **Smaller Final Image**: Build tools (gcc, build-essential) not included in runtime
3. **Two-Stage Separation**:
   - Builder stage: Runs bench init, installs apps, clears .git
   - Final stage: Copies only necessary artifacts (frappe-bench directory)
4. **Proven Pattern**: Used by Frappe Foundation in official ERPNext deployments

**Alternative Considered**: Full control Containerfile
- Rejected: More maintenance burden, must track Python/Node versions manually
- Use only if needing special hardening or custom system packages

---

### Service Composition Decision: SEPARATE SERVICES
**Recommendation**: 6-7 service deployment (not `bench start`)

**Services**:
1. configurator - One-shot init
2. backend - Gunicorn (port 8000)
3. frontend - Nginx (port 8080)
4. websocket - Node Socket.IO (port 9000)
5. queue-short - Worker (short jobs)
6. queue-long - Worker (long jobs)
7. scheduler - Background jobs

**Rationale**:
- `bench start` bundles everything via Procfile (not container-friendly)
- Separate services = independently scalable
- Better health checking per service
- Matches production patterns

---

### Database Decision: MARIADB 11.8
**Recommendation**: MariaDB 11.8 with docker-compose override

**Rationale**:
- Latest stable, well-tested with Frappe v15
- Built-in healthcheck support
- Alpine not suitable (needs full MySQL compatibility)
- PostgreSQL option available but MariaDB is Frappe default

**Config**:
```yaml
MYSQL_ROOT_PASSWORD: ${DB_PASSWORD}
MARIADB_AUTO_UPGRADE: 1
Healthcheck: mariadb healthcheck.sh
```

---

### Redis Decision: TWO INSTANCES
**Recommendation**: Separate redis-cache and redis-queue

**Rationale**:
- Cache failures don't block job queue
- Queue data persistence important (socket.io events, background jobs)
- Cache can be ephemeral (in-memory)

**Persistence**:
- redis-cache: No volume (ephemeral)
- redis-queue: Persistent volume (survives restart)

---

### Environment Strategy: .env Files
**Recommendation**: Three-tier .env approach
1. `.env.example` - All possible variables with defaults
2. `.env.production` - Production secrets (encrypted)
3. `.env.development` - Local testing settings

**Security**:
- Never commit actual passwords
- Use Docker secrets for production
- Example provided in frappe_docker/example.env

---

### Port Configuration Decision
**Frontend**: 8080 (standard for LMS access)
**Backend**: 8000 (internal, not exposed)
**Socket.IO**: 9000 (proxied through frontend)

**Rationale**: Matches Frappe Docker defaults, single entry point for security

---

### Site Initialization Decision: CONTAINERIZED SETUP
**Recommendation**: Initialize site within container (not pre-built)

**Pattern**:
```bash
docker compose exec backend bench new-site lms.localhost \
  --mariadb-user-host-login-scope='%' \
  --install-app frappe \
  --install-app lms
```

**Rationale**:
- Flexible multi-site setup
- Database created dynamically
- Apps installed at runtime (faster iteration)
- Matches Frappe Docker example patterns

---

### Volume Strategy Decision: THREE MOUNTS
**Recommendation**: Persistent volumes for sites, assets, logs

```yaml
volumes:
  sites:           # /home/frappe/frappe-bench/sites (config, DB backups)
  assets:          # /home/frappe/frappe-bench/sites/assets (CSS, JS, media)
  logs:            # /home/frappe/frappe-bench/logs (application logs)
  db-data:         # MariaDB persistent storage
  redis-queue:     # Redis queue persistence
```

**Rationale**:
- sites: Critical for multi-site and backup strategies
- assets: Static assets (CSS, JS compiled)
- logs: Debugging and monitoring
- DB data: Prevent data loss on container restart

---

