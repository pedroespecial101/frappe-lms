---
trigger: always_on
---

## Server Startup
**ALWAYS** use `./start_server.sh` or `honcho start` to run the development server. **DO NOT** use `bench start` directly as it fails due to environment issues. The server runs on port **9001**.

## Frappe Framework Context

This LMS is built on the **Frappe Framework**. Use the following Context7 library IDs for documentation:

- `/websites/frappe_io-framework-user-en` - Framework User Manual
- `/websites/frappe_io-framework` - Official Documentation
- `/websites/frappe_io_framework` - Technical Documentation
- `/frappe/frappe` - Frappe Core Repository & Docs
- `/websites/frappe_io` - General Frappe Apps Documentation

Official website: [frappeframework.com/docs](https://frappeframework.com/docs/)
More details: .agent/rules/frappe_framework.md
## Documentation Priority

When working on this Frappe LMS project, refer to these files for understanding the codebase:

### Import & Data Structure
**Read `import_scripts.md`** before:
- Modifying course import functionality
- Working with LMS DocTypes (LMS Course, Course Chapter, Course Lesson)
- Understanding video embedding options
- Troubleshooting import issues

### Key Files
- `import_scripts.md` - Import documentation and data structure guide
- `CLAUDE.md` - Project overview and quick reference
- `templates/combined_modules_withLocalURL.json` - Source course data
- `lms/scripts/import_gcse_course.py` - Main import script

### Always Update
- `changelog.md` - Record all changes (most recent at top)
