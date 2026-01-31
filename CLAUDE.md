# Frappe LMS Workspace Rules

## Project Overview

This is a customized Frappe LMS (Learning Management System) project built on the **Frappe Framework**. It includes additional course import functionality for video-based courses.

## Frappe Framework Documentation

This project is built using the Frappe Framework (`frappe >= 15.0.0`). AI agents should use the following Context7 library IDs to access official documentation:

- `/websites/frappe_io-framework-user-en` - Framework User Manual
- `/websites/frappe_io-framework` - Official Documentation
- `/websites/frappe_io_framework` - Technical Documentation
- `/frappe/frappe` - Frappe Core Repository & Docs
- `/websites/frappe_io` - General Frappe Apps Documentation

Official website for documentation: [frappeframework.com/docs](https://frappeframework.com/docs/)


## Important Documentation

### Import & Data Structure

**If you need to understand course importing, data structures, or the LMS schema**, read:
- **`import_scripts.md`** - Comprehensive guide to importing courses, including:
  - Frappe LMS data hierarchy (Course → Chapter → Lesson)
  - Import script documentation (`lms/scripts/import_gcse_course.py`)
  - Source data format (JSON structure)
  - Video embedding options (macros, EditorJS, YouTube)
  - API reference for programmatic course creation
  - Troubleshooting common issues

### Source Data

- **`templates/combined_modules_withLocalURL.json`** - Main course data with modules and videos
- Video assets are symlinked from external directory

## Key Directories

| Directory | Purpose |
|-----------|---------|
| `lms/lms/doctype/` | Frappe DocType definitions |
| `lms/lms/api.py` | API endpoints |
| `lms/scripts/` | Custom import scripts |
| `templates/` | JSON data files |
| `frontend/` | Vue.js frontend components |

## Related Projects

- Bench directory: `../lms-bench/`
- Video assets: Symlinked to external Mathmo-videos directory

## Running the LMS

**IMPORTANT**: 
- **Start Command**: ALWAYS use `./start_server.sh` (or `honcho start` inside the activated bench). **DO NOT** use `bench start` as it fails to detect the process manager.
- **Port**: The web server runs on port **9001**.
- **Services**: The script handles starting MariaDB and Redis for you.

```bash
./start_server.sh
```

## Running Imports

```bash
cd ../lms-bench
bench --site lms.localhost execute lms.scripts.import_gcse_course.run_import
```
