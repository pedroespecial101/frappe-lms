# Issues - Frappe LMS Dockerization

## Session: ses_3eb324a00ffejrWUFevRPg1686
**Started**: 2026-01-31T16:34:07.713Z

---


## BLOCKER: Docker Not Available - 2026-01-31

### Remaining Tasks Blocked (12/23)
All remaining tasks require Docker daemon to be running for testing/verification:

**Phase 2: Dockerfile Creation**
- Task 2.3: Test build caching (needs `docker build`)

**Phase 4: Entrypoint Script**
- Task 4.3: Test idempotency logic (needs running containers)

**Phase 5: Integration Testing (7 tasks)**
- Task 5.1: First boot test
- Task 5.2: Health check verification
- Task 5.3: Service accessibility
- Task 5.4: Database verification
- Task 5.5: Redis verification
- Task 5.6: Site login test
- Task 5.7: Video mount verification

**Phase 6: Persistence Testing (3 tasks)**
- Task 6.1: Stop containers
- Task 6.2: Verify volumes exist
- Task 6.3: Restart and verify data

### Current Status
- Docker daemon not running on development machine
- Cannot execute `docker build`, `docker compose up`, or `docker exec` commands
- All deliverables (files) are complete and ready for testing

### Next Steps
1. **Option A**: Deploy to unRAID and run tests there
2. **Option B**: Start Docker Desktop locally and continue testing
3. **Option C**: Mark remaining tasks as "Ready for Integration Testing" and consider work complete

### Completed Without Docker (11/23)
All file creation and documentation tasks completed successfully:
- Research ✓
- .dockerignore ✓
- Dockerfile.unraid ✓
- docker-compose.unraid.yml ✓
- .env.unraid.example ✓
- docker/entrypoint.sh ✓
- Compose validation (syntax only) ✓
- README-UNRAID.md with all sections ✓

---

## Frontend Build Issue - 2026-01-31

### Problem
Docker build fails at frontend stage with error:
```
Could not resolve "../../../../sites/common_site_config.json" from "src/socket.js"
```

### Root Cause
- `frontend/src/socket.js` imports `socketio_port` from `../../../../sites/common_site_config.json`
- This file doesn't exist during Docker build time (it's created at runtime)
- Frontend expects to be built within a running Frappe bench environment

### Analysis
This is a design issue with Frappe LMS frontend:
1. Static import of runtime config file
2. Build requires bench workspace structure to be present
3. Frontend is tightly coupled to Frappe bench file structure

### Possible Solutions

**Option A: Skip Frontend Build (Use Pre-Built Assets)**
- Remove frontend-build stage from Dockerfile
- Rely on runtime `bench build` command in entrypoint
- Slower first startup but works with existing code

**Option B: Mock Config File During Build**
- Create temporary common_site_config.json with default socketio_port
- Build frontend with mocked file
- Real config used at runtime

**Option C: Patch socket.js**
- Modify import to use dynamic import or window variable
- Requires code change to LMS source

**Option D: Build Frontend at Runtime**
- Remove frontend-build stage entirely
- Add `bench build --app lms` to entrypoint script
- First boot will be slower (~10 minutes)

### Recommendation: Option D (Build at Runtime)
Most compatible with Frappe ecosystem patterns. Official Frappe Docker builds apps at image creation time, but for custom LMS with local changes, runtime build is more flexible.

---

## Dockerfile Build Broken by redis-tools Addition - 2026-01-31

### Problem
Attempting to add `redis-tools` to Dockerfile resulted in accidentally removing build dependencies (gcc, g++, make, libmariadb-dev, etc.) from python-deps stage.

### Impact
- Docker build fails at `bench init` step
- Error: "gcc is not installed" when building psutil
- Cannot complete integration testing tasks (5.1-5.7, 6.1-6.3)

### Root Cause
Subagent over-simplified the apt-get install command in python-deps stage, removing critical build tools needed for Python package compilation.

### Required Fix
The python-deps stage needs BOTH runtime and build dependencies:
- Runtime: git, curl, wget, nginx, mariadb-client, redis-tools, wkhtmltopdf, fonts
- Build tools: gcc, g++, make, libmariadb-dev, libpq-dev, libffi-dev, liblcms2-dev, libldap2-dev, libsasl2-dev, libjpeg62-turbo-dev, zlib1g-dev

### Status
BLOCKED - Cannot proceed with integration testing without working Docker image.

### Time Spent
- ~45 minutes debugging Dockerfile issues
- Multiple rebuild attempts
- Need to revert to working state or fix build dependencies

### Recommendation
Due to time constraints in boulder session:
1. **Option A**: Revert Dockerfile to last working version (before redis-tools changes)
2. **Option B**: Delegate Dockerfile fix as separate urgent task
3. **Option C**: Document as known issue and mark integration tests as "Docker build blocked"

---
