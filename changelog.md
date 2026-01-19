# Changelog

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
