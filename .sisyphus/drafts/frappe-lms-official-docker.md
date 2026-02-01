# Draft: Frappe LMS Official Docker Migration

## Requirements (confirmed)

### User's Goal
Migrate from custom Dockerfile to official Frappe Docker images (`frappe/frappe_docker`) by:
1. Auditing ALL customizations (compare local code vs original git commit f297f263)
2. Determining if customizations can be applied to official Docker setup
3. Using official Docker images as base + layering our modifications

### Key Customizations Identified (from git diff)

#### CRITICAL (Must Work):
1. **Custom video streaming endpoint** (`lms/lms/video.py`) - RFC 7233 byte-range support for video seeking
2. **VideoBlock.vue modification** - Routes `/files/` URLs through streaming endpoint
3. **Import scripts** - `lms/scripts/import_gcse_course.py` for bulk video course import

#### MINOR (Nice to Have):
4. **Course sorting change** (`lms/lms/utils.py`) - Changed from "enrollments desc" to "creation desc"
5. **Helper scripts** - `start_server.sh`, `setup_env.sh`
6. **Documentation** - `import_scripts.md`, `CLAUDE.md`, changelog.md

#### NEW FILES (Data/Config):
7. **Video course data** - `templates/combined_modules_withLocalURL.json`
8. **Additional scripts** - `scripts/add_video_runtimes.py`, `lms/scripts/update_course_images.py`

### Technical Decisions

**Official Docker Approach**: Use `frappe/frappe_docker` repository's `images/layered/Containerfile` with `APPS_JSON_BASE64` build arg
- This is the **official** method for custom apps
- Apps are built into image at **build time** (not runtime)
- Docker immutability principle: containers are immutable, apps must be baked in

**Build Strategy**:
```bash
# Option 1: Point apps.json to GitHub repo (after pushing changes)
apps.json → https://github.com/pedroespecial101/frappe-lms

# Option 2: Use local path during build (for testing)
apps.json → file:///path/to/local/frappe-lms
```

### Research Findings

**From Librarian Agent**:
- Official `frappe/frappe_docker` repo uses 3-image architecture:
  - `frappe/bench` (dev base)
  - `frappe/base` (production runtime, slim)
  - `frappe/build` (intermediate build stage with compilers)
- `images/layered/Containerfile` is the official custom app pattern
- Uses `APPS_JSON_BASE64` build arg to specify apps at build time
- Multi-stage build: builder stage installs apps → copies bench to runtime image
- Production `compose.yaml` uses same image for all services (backend, frontend, websocket)

**From Git Diff Analysis**:
- Only **2 core LMS files modified**: `VideoBlock.vue`, `utils.py`
- **1 new LMS module added**: `video.py`
- **3 import scripts added**: All in `lms/scripts/`
- No changes to `hooks.py` (good - no custom Frappe hooks to migrate)
- No changes to app structure or dependencies

### Scope Boundaries

**INCLUDE**:
- Complete audit of customizations (verify changelog.md is accurate)
- Migration to official `frappe/frappe_docker` setup
- Deployment to unRAID server with same video volume mounts
- Verification that video streaming works end-to-end

**EXCLUDE**:
- Modifying the custom LMS code itself (preserve as-is)
- Changing the import scripts or data format
- Touching the video files themselves (`/mnt/m2cache/mathmo-videos/`)

### Open Questions

**ANSWERED**:
- ✅ Can we access original git version? YES - commit f297f263 exists in history
- ✅ Is changelog.md complete? VERIFIED via git diff
- ✅ Can official Docker work with our mods? YES - layered/Containerfile supports this
- ✅ Do we have git repo? YES - already forked to pedroespecial101/frappe-lms

**PENDING USER DECISION**:
- Should we push our changes to GitHub first, or test with local build?
- Do we want CI/CD pipeline (GitHub Actions) or manual builds?
- Keep existing unRAID setup or start fresh with official compose.yaml?

## Next Steps

1. Consult Metis for gap analysis
2. Generate comprehensive work plan
3. Present to user with decision points
