# Changelog

## [2026-04-02]
- Resolved missing CSS on the login and landing pages by rebuilding and synchronizing frontend assets.
- Implemented automatic site resolution with symlinks for `localhost`, `127.0.0.1`, and `optiplex3070-1` to prevent "Not Found" 404 errors.
- Updated `docker/entrypoint.sh` to handle asset building and hostname resolution permanently.
- Provided default administrator login credentials (`Administrator` / `admin`).
- Fixed unhealthy container status by ensuring `current_site.txt` is always set on startup.
- Configured `host_name` in `site_config.json` to allow access via `optiplex3070-1:9001`.
- Updated `entrypoint.sh` to be more robust for site initialization on restarts.
- Resolved 404 errors for internal health check and external access.

## [2026-04-02]
- Fixed `vite: not found` error in `Dockerfile.unraid` by adding `node_modules/.bin` to PATH during build.
- Updated `implementation_plan.md` and `task.md` for unRAID deployment completion.
- Verified unRAID server connectivity and existing container status.

## 2026-03-31

### Docker Redeployment Fixes for unRAID
- **Fixed** Redis connection string format in `.env` and `.env.unraid.example` (standardized to `host:port/db` format)
- **Fixed** `docker/entrypoint.sh`:
  - Added `--mariadb-user-host-login-scope='%'` to `bench new-site` (critical for Docker networking)
  - Fixed Redis URL parsing to handle `host:port/db` format correctly
  - Added `lms` to `sites/apps.txt` (previously only wrote `frappe`)
  - Added `bench use $SITE_NAME` after site creation
  - Added automatic video symlink creation: `/app/videos/*.mp4` → `sites/lms.localhost/public/files/`
- **Updated** `docker-compose.unraid.yml`: video mount path changed to `/mnt/user/mathmo-assets`
- **Updated** `README-UNRAID.md`: corrected all video path references, added symlink verification step

## 2026-01-20

### Course Image Update
- Generated custom course images for 12 modules using "Nano Banana Pro" style (Imagen 3)
- Updated LMS Course records to use the new images via `scripts/update_course_images.py`
- Images are served from `/public/files/` in the LMS site
- Changed web server port from 8000 to **9001** (web) and socketio to 9000 to avoid conflicts
- **Infrastructure Change**: Switched startup process to use `honcho start` directly (via `start_server.sh`) instead of `bench start` to resolve process manager detection issues.

## 2026-01-19

### Script: Video Runtime Analysis
- Created `scripts/add_video_runtimes.py` to analyze video durations using ffprobe
- Added `runtime_seconds` and `runtime_formatted` fields to each video in `combined_modules_withLocalURL.json`
- **Total videos analyzed**: 347
- **Total runtime**: 51h 4m 38s (183,878.36 seconds)

---

## 2026-01-19

### Documentation: Build Process Guide
- Created `.gemini/build_process.md` documenting the split between frappe-lms source and lms-bench runtime
- Documented workflow for syncing changes: copy files → bench build → hard refresh
- Included common issues and troubleshooting tips

### Fix: Video Seeking (Skip Forward/Backward)
- **Root Cause**: Frappe's static file middleware (Werkzeug `SharedDataMiddleware`) does not support HTTP byte-range requests
- **Solution**: Created custom video streaming endpoint `lms/lms/video.py` with full RFC 7233 byte-range support
- Updated `VideoBlock.vue` to route local `/files/` video URLs through the new streaming endpoint
- Videos now properly support seeking via slider without restarting from the beginning

---

## 2026-01-19

### Documentation: Frappe Framework Rules & Documentation
- Added Frappe Framework context and documentation links to `.gemini/rules.md`
- Included Context7 library IDs for instant documentation access
- Verified framework version range: `frappe >= 15.0.0`

## 2026-01-19

### Bugfix: Video Playback with Directory Symlinks
- Discovered Frappe `StaticDataMiddleware` bug: directory-level symlinks for `public/files` cause 500/404 errors
- Root cause: Middleware checks `is_relative_to()` against unresolved symlink path after resolving file path
- **Resolution**: Copied video files directly into `public/files/` instead of using directory symlink
- Updated `import_scripts.md` with detailed troubleshooting documentation

### Utility: Server Startup Script
- Created `start_server.sh` to automate:
  - Starting MariaDB and Redis services
  - **Gracefully cleaning up stale processes and PID files to prevent startup errors**
  - Navigating to `lms-bench` and activating virtual environment
  - Running `bench start`

### Import: GCSE Video Vault 2 & Local Assets
- Re-imported course as "GCSE Video Vault 2"
- Updated `import_gcse_course.py`:
  - Prioritizes local file paths over remote URLs
  - Implemented direct SQL insertion for `File` records to bypass 25MB upload limit
- Replaced `public/files` directory with symlink to `mathmo_assets` for direct local file serving
- Verified correct video playback from local disk

### Documentation: Import Scripts and Data Structure Guide
- Created `import_scripts.md` with comprehensive documentation on:
  - Frappe LMS data hierarchy (Course → Chapter → Lesson)
  - Import script usage and API reference
  - Source JSON data format and mapping
  - Video embedding options (macros, EditorJS, YouTube)
  - Troubleshooting guide
- Created `CLAUDE.md` workspace rules file for AI assistants
- Created `.gemini/rules.md` for Gemini-specific workspace rules
- All documentation directs to `import_scripts.md` for import/data structure questions

### Import: GCSE Video Vault Course Created
- Successfully imported 12 chapters and 307 lessons from `combined_modules_withLocalURL.json`
- Created import script at `lms/scripts/import_gcse_course.py`
- Video paths transformed from `mathmo_assets/` to `/assets/` for web access
- Created symlink `assets` → `/Users/petetreadaway/Projects/Mathmo-videos/mathmo_assets`
- Course published and available at `/lms/courses/gcse-video-vault`

### Research: LMS Import Capabilities
- Analyzed Frappe LMS import utilities and SCORM support
- Found SCORM support exists at Chapter level for interactive packages (not suitable for plain video content)
- Identified built-in Data Import UI at `/lms/data-import` (CSV-based, limited to Courses/Batches/Categories)
- Documented API endpoints for programmatic creation (`upsert_chapter`, `add_lesson`)
- Discovered video embedding options: YouTube field, `{{ Video() }}` macro for MP4 files, VideoBlock component
- Created data mapping guide from `combined_modules_withLocalURL.json` to Frappe LMS structure
- Recommended custom Python import script approach for bulk video course import
