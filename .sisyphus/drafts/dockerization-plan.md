# Draft: Frappe LMS Dockerization for unRAID

## Requirements (confirmed)
- **Target Environment**: unRAID server
- **Build Strategy**: Local Docker image build (not published to Docker Hub)
- **Deployment**: Docker Compose file that "just works"
- **Scope**: Full stack including lms-bench and all dependencies

## Current Architecture Understanding

### Project Structure
1. **frappe-lms** (`/Users/petetreadaway/Projects/frappe-lms`)
   - The LMS app source code
   - Location: Should live in bench's `apps/lms` directory
   - Contains: Python package, frontend Vue.js app, DocTypes, API endpoints
   - Import scripts: `lms/scripts/import_gcse_course.py`

2. **lms-bench** (`/Users/petetreadaway/Projects/lms-bench`)
   - Frappe bench workspace
   - Contains:
     - `apps/` - Installed apps (frappe, lms)
     - `sites/` - Site instances (lms.localhost)
     - `config/` - Redis configs, Procfile
     - `env/` - Python virtual environment

3. **Video Assets**
   - External symlinked directory (Mathmo-videos)
   - Need to handle in Docker context

### Runtime Dependencies (from Procfile and configs)

**Services Required:**
1. **MariaDB** (10.8+)
   - Character set: utf8mb4
   - Collation: utf8mb4_unicode_ci
   
2. **Redis** (3 instances)
   - redis_cache (port 13000 locally, 6379 in container)
   - redis_queue (port 11000 locally, 6379 in container)
   - redis_socketio (uses cache instance)

3. **Node.js** (for socketio)
   - From Procfile: `/Users/petetreadaway/.nvm/versions/node/v22.16.0/bin/node apps/frappe/socketio.js`

4. **Python Services** (via bench)
   - web: bench serve (port 9001)
   - worker: bench worker (background jobs)
   - schedule: bench schedule (cron tasks)
   - socketio: node socketio.js (port 9000)
   - watch: bench watch (frontend rebuilds) - can be optional in prod

### Current Startup Process (start_server.sh)
1. Start MariaDB via brew
2. Start Redis via brew
3. Kill processes on ports 13000, 11000, 9000, 9001, 8000
4. Remove stale PID files
5. CD to lms-bench
6. Activate virtualenv
7. Run `honcho start` (reads Procfile)

### Existing Docker Setup (docker/docker-compose.yml)
- Simple 3-service setup: mariadb, redis, frappe
- Uses `frappe/bench:latest` image
- Runs init.sh script that:
  - Initializes new bench
  - Gets lms app
  - Creates site
  - Installs app
  - Starts bench

**Problem with existing setup:**
- Doesn't account for local development changes
- Doesn't handle video assets
- Doesn't preserve site data
- Uses generic bench image instead of custom build

## Technical Decisions

### Multi-Stage Docker Build Approach
**Decision**: Create a multi-stage Dockerfile that:
1. Stage 1: Build frontend assets
2. Stage 2: Setup Python environment and dependencies
3. Stage 3: Final runtime image with bench + apps

**Rationale**: 
- Smaller final image
- Separate build dependencies from runtime
- Easier to cache layers

### Volume Strategy
**Decision**: Use named volumes for:
- MariaDB data persistence
- Site files persistence
- Video assets (bind mount or volume)

**Rationale**:
- Data survives container restarts
- unRAID can easily backup named volumes
- Video assets can be bind-mounted from host if needed

### Network Architecture
**Decision**: Use Docker Compose networks
- Backend network (mariadb, redis, frappe services)
- Frontend exposed via ports

**Rationale**:
- Security isolation
- Service discovery via hostname
- Standard Docker networking

### Redis Architecture
**Decision**: Single Redis container with multiple databases (0, 1, 2)
- Database 0: cache
- Database 1: queue
- Database 2: socketio

**Rationale**:
- Simpler than 3 separate Redis instances
- Frappe supports Redis database separation
- Less resource overhead

### Image Build Strategy
**Decision**: Build custom image including:
- Frappe framework (version 15)
- LMS app
- All Python/Node dependencies
- Pre-built frontend assets

**Rationale**:
- Faster container startup
- No internet dependency at runtime
- Reproducible builds

### Site Initialization Strategy
**Decision**: Use entrypoint script that:
- Checks if site exists
- Creates site on first run
- Starts bench services on subsequent runs

**Rationale**:
- Idempotent startup
- Works with volume persistence
- No manual setup needed

## Open Questions
None - all architectural decisions made.

## Scope Boundaries

### INCLUDE:
- Complete Docker Compose stack
- Custom Dockerfile for Frappe + LMS
- Entrypoint script for initialization
- Volume definitions for persistence
- Port mappings for access
- Environment variable configuration
- Health checks for services
- README with deployment instructions

### EXCLUDE:
- Nginx reverse proxy (can be added by user)
- SSL/TLS certificates (unRAID handles this)
- Backup strategies (unRAID has built-in tools)
- Multi-site setup (single site: lms.localhost)
- Production hardening beyond basics
- Monitoring/logging infrastructure
- Auto-scaling configurations

## Deliverables

1. **Dockerfile** - Multi-stage build for Frappe + LMS
2. **docker-compose.yml** - Complete stack definition
3. **entrypoint.sh** - Container initialization script
4. **bench-config/** - Configuration templates
5. **README-DOCKER.md** - Deployment guide for unRAID
6. **.dockerignore** - Optimize build context

## Test Strategy Decision
- **Infrastructure exists**: Docker only, no test framework in project
- **User wants tests**: Manual verification procedures
- **QA approach**: Manual verification via browser and CLI commands

## Manual Verification Procedures

Each component will include verification steps:
1. **MariaDB**: Connect and query
2. **Redis**: Ping and verify databases
3. **Frappe Web**: Access http://localhost:9001
4. **LMS App**: Access http://localhost:9001/lms
5. **Import Script**: Run course import
6. **Video Playback**: Verify video assets accessible
