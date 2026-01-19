# Frappe LMS Course Import Guide

This document explains how to import course content into Frappe LMS, including the data structures, scripts, and methodologies used.

## Table of Contents

1. [Overview](#overview)
2. [Frappe LMS Data Structure](#frappe-lms-data-structure)
3. [Import Script](#import-script)
4. [Source Data Format](#source-data-format)
5. [Data Mapping](#data-mapping)
6. [Video Embedding Options](#video-embedding-options)
7. [Running the Import](#running-the-import)
8. [Troubleshooting](#troubleshooting)

---

## Overview

Frappe LMS uses a hierarchical document structure for course content. This project includes custom import scripts to programmatically create courses from JSON data files.

### Key Files

| File | Purpose |
|------|---------|
| `lms/scripts/import_gcse_course.py` | Main import script |
| `templates/combined_modules_withLocalURL.json` | Source data with module/video information |
| `lms/lms/doctype/` | Frappe DocType definitions for LMS entities |

---

## Frappe LMS Data Structure

### Hierarchy

```
LMS Course
├── Course Instructor (child table - required)
├── Chapter Reference (child table - links to chapters)
│   └── Course Chapter
│       ├── Lesson Reference (child table - links to lessons)
│       │   └── Course Lesson
│       └── SCORM Package (optional)
└── Related Courses (child table - optional)
```

### DocType: LMS Course

Location: `lms/lms/doctype/lms_course/lms_course.json`

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `title` | Data | ✅ | Course title |
| `short_introduction` | Small Text | ✅ | Brief description |
| `description` | Text Editor | ✅ | Full HTML description |
| `instructors` | Table MultiSelect | ✅ | Links to User documents |
| `chapters` | Table | | Links to Chapter Reference |
| `published` | Check | | Whether course is visible |
| `featured` | Check | | Show on homepage |
| `video_link` | Data | | YouTube embed link for course intro |
| `image` | Attach Image | | Course preview image |
| `category` | Link | | LMS Category reference |

### DocType: Course Chapter

Location: `lms/lms/doctype/course_chapter/course_chapter.json`

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `title` | Data | ✅ | Chapter title |
| `course` | Link | ✅ | Parent LMS Course |
| `lessons` | Table | | Links to Lesson Reference |
| `is_scorm_package` | Check | | Enable SCORM mode |
| `scorm_package` | Link | | SCORM package file |

### DocType: Course Lesson

Location: `lms/lms/doctype/course_lesson/course_lesson.json`

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `title` | Data | ✅ | Lesson title |
| `chapter` | Link | ✅ | Parent Course Chapter |
| `course` | Link | | Auto-fetched from chapter |
| `body` | Markdown Editor | | Legacy content (markdown with macros) |
| `content` | Text | | EditorJS JSON content (preferred) |
| `youtube` | Data | | YouTube video URL |
| `include_in_preview` | Check | | Visible without enrollment |
| `quiz_id` | Data | | Associated quiz |

### Child Tables

#### Chapter Reference
Links chapters to courses with ordering:
- `chapter`: Link to Course Chapter
- `idx`: Order within course
- `parent`: LMS Course name

#### Lesson Reference  
Links lessons to chapters with ordering:
- `lesson`: Link to Course Lesson
- `idx`: Order within chapter
- `parent`: Course Chapter name

---

## Import Script

### Location
`lms/scripts/import_gcse_course.py`

### Functions

#### `run_import()`
Main entry point that orchestrates the import:
1. Loads JSON data from `templates/combined_modules_withLocalURL.json`
2. Deletes existing course if present (for clean re-import)
3. Creates LMS Course document
4. Iterates through modules to create chapters
5. Creates lessons for each video
6. Publishes the course

#### `create_course(title)`
Creates the main LMS Course document with:
- Title and descriptions
- Administrator as default instructor
- Featured flag enabled

#### `create_chapter(course, module_data, idx)`
Creates a Course Chapter from module data:
- Sets title from `module_name`
- Links to parent course
- Creates Chapter Reference for ordering

#### `create_lesson(course, chapter, video_data, idx)`
Creates a Course Lesson from video data:
- **Prioritizes local file paths** from the JSON data.
- Automatically transforms `mathmo_assets/` paths to `/files/`.
- Calls `ensure_file_record` to guarantee the file exists in the database.
- Falls back to `video_direct_url` (Wistia) if no local file is found.
- Creates both `body` (markdown macro) and `content` (EditorJS JSON).
- Creates Lesson Reference for ordering.

#### `ensure_file_record(filename, file_url)`
**Critical Helper Function**: 
- Checks if a `File` document exists for the given path.
- If missing, **inserts a new record using raw SQL**.
- **Reason**: Using `frappe.new_doc("File")` triggers validation hooks that check for physical file existence (which is fine) but also enforces **Max File Size** limits (default 25MB). Since our video assets are already on disk and likely >25MB, standard ORM insertion fails. Bypassing validation with SQL allows us to register these existing assets safely.

#### `delete_course(course_name)`
Removes existing course and all related documents:
1. Gets all chapters for the course
2. Deletes lesson references and lessons for each chapter
3. Deletes chapter references and chapters
4. Deletes the course document

---

## Source Data Format

### JSON Structure

```json
[
  {
    "module_name": "Module Title",
    "module_id": "2156841131",
    "module_number": 0.1,
    "videos": [
      {
        "title": "Lesson Title",
        "subtitle": "Optional description",
        "url": "https://source-website.com/...",
        "wistia_id": "slidifntia",
        "video_direct_url": "https://embed-ssl.wistia.com/deliveries/xxx.mp4",
        "quality": "720p",
        "video_number": 1,
        "local_path": "mathmo_assets/wistia_slidifntia.mp4"
      }
    ]
  }
]
```

### Field Descriptions

| Field | Type | Description |
|-------|------|-------------|
| `module_name` | string | Chapter title |
| `module_id` | string | External identifier |
| `module_number` | float | Ordering (0.1, 0.2, 1, 2, etc.) |
| `videos` | array | List of video lessons |
| `videos[].title` | string | Lesson title |
| `videos[].subtitle` | string | Additional description |
| `videos[].video_direct_url` | string | Direct MP4 URL (fallback) |
| `videos[].local_path` | string | **Primary video source**. Path to local file. |
| `videos[].video_number` | int | Order within module |
| `videos[].quality` | string | Video quality indicator |

---

## Data Mapping

### Module → Chapter

| Source JSON | Target DocType | Target Field |
|-------------|---------------|--------------|
| `module_name` | Course Chapter | `title` |
| `module_number` | Chapter Reference | `idx` (ordering) |
| (parent course) | Course Chapter | `course` |

### Video → Lesson

| Source JSON | Target DocType | Target Field |
|-------------|---------------|--------------|
| `title` | Course Lesson | `title` |
| `local_path` | File | `file_url` (transformed to /files/...) |
| `local_path` | Course Lesson | `body` (via Video macro) |
| `local_path` | Course Lesson | `content` (EditorJS format) |
| `video_number` | Lesson Reference | `idx` (ordering) |
| (parent chapter) | Course Lesson | `chapter` |

---

## Handling Large Local Files

When importing large video assets that are already present on the server filesystem (e.g., via symlink), standard Frappe file creation methods might fail.

### The Problem
`frappe.new_doc("File").insert()` triggers the `before_insert` hook, which calls `check_max_file_size()`. If your local videos exceed the system limit (default 25MB), the import will crash with `MaxFileSizeReachedError`, even though you aren't actually uploading a new file.

### The Solution
Use **direct SQL insertion** to create the `File` metadata record. This skips the Python-level hooks and validation layer.

```python
frappe.db.sql("""
    INSERT INTO `tabFile` 
    (name, creation, modified, modified_by, owner, docstatus, idx,
     file_name, file_url, is_private, is_home_folder, is_attachments_folder, 
     file_size, folder)
    VALUES 
    (%s, NOW(), NOW(), 'Administrator', 'Administrator', 0, 0,
     %s, %s, 0, 0, 0, 
     0, 'Home')
""", (frappe.generate_hash(), filename, file_url))
frappe.db.commit()
```
*Note: We set `file_size` to 0 to avoid errors; this doesn't affect playback.*

---

## Video Embedding Options

### 1. Local Files (Preferred)
Files served from `sites/[site]/public/files/` (via symlink or direct copy).
- **URL**: `/files/video.mp4`
- **Requires**: A corresponding record in the `tabFile` table.

### 2. Direct CDN URLs
External links (e.g., Wistia, S3).
- **URL**: `https://embed-ssl.wistia.com/...`
- **Requires**: No `tabFile` record needed.

### 3. YouTube Field
Standard YouTube embedding via the `youtube` field on `Course Lesson`.

---

## Running the Import

### Prerequisites

1. Frappe Bench installed and running
2. LMS app installed on the site
3. Source JSON file in place
4. **Symlink established**: `lms-bench/sites/[site]/public/files` -> `mathmo_assets`

### Command

From the bench directory:
```bash
bench --site [site-name] execute lms.scripts.import_gcse_course.run_import
```

For this project:
```bash
cd /path/to/lms-bench
bench --site lms.localhost execute lms.scripts.import_gcse_course.run_import

### Alternative: Import Modules as Separate Courses

To import each module from the JSON as a distinct LMS Course:

```bash
bench --site lms.localhost execute lms.scripts.import_modules_as_courses.run_import
```
```

### After Import

1. Visit `/lms/courses/[course-slug]` to view the course
2. Check the Frappe desk for course management
3. Test video playback in lessons

---

## Troubleshooting

### Common Issues

#### "MaxFileSizeReachedError"
**Symptom**: Import crashes when creating lessons for large videos.
**Solution**: See "Handling Large Local Files" above. Use raw SQL to insert File records.
**Alternative**: Increase system file size limit in "System Settings", but SQL bypass is faster/safer for bulk imports.

#### Videos Not Playing
**Symptom**: Video player shows but video doesn't load.
**Solutions**:
1. Check `tabFile` exists: `SELECT * FROM tabFile WHERE file_name = 'video.mp4'`
2. Verify files exist in `public/files/` directory.
3. Check browser console for 404 errors on the `/files/...` URL.

#### ⚠️ Symlink Directory Bug (Frappe Middleware Issue)
**Symptom**: Videos return 500/404 errors even though the symlink and files exist.
**Root Cause**: Frappe's `StaticDataMiddleware` (in `apps/frappe/frappe/middlewares.py`) has a bug when the entire `public/files` directory is a symlink:
```python
# In middlewares.py line 24:
if not path.is_relative_to(files_path) or not path.is_file():
    raise NotFound
```
When `files_path` is a symlink (e.g., `/path/public/files -> /external/videos`), the middleware:
1. Resolves the full file path to the **actual location** (e.g., `/external/videos/video.mp4`)
2. But checks against the **unresolved** `files_path` symlink
3. Since `/external/videos/video.mp4` is NOT relative to `/path/public/files`, it fails

**Solution**: Do NOT use a directory-level symlink for `public/files`. Instead:
- **Option A (Recommended)**: Copy video files directly into `public/files/`
- **Option B**: Create a real `public/files/` directory with individual symlinks per file:
  ```bash
  mkdir public/files
  for file in /external/videos/*.mp4; do
      ln -s "$file" "public/files/$(basename "$file")"
  done
  ```

**Note**: This is a Frappe core bug, not an LMS issue. It affects any site using directory symlinks for static files.

#### Unknown Column in SQL
**Symptom**: `OperationalError: (1054, "Unknown column 'is_home_page' ...")`
**Solution**: The column reference for the "Home" folder flag is `is_home_folder`, not `is_home_page`. Check your DB schema with `DESCRIBE tabFile`.

---

## SCORM Support

Frappe LMS supports SCORM packages at the **chapter level**, not individual lessons.

### SCORM Fields on Course Chapter

- `is_scorm_package`: Enable SCORM mode
- `scorm_package`: Link to uploaded ZIP file
- `scorm_package_path`: Extracted content path
- `manifest_file`: imsmanifest.xml location
- `launch_file`: Entry point HTML file

### Key Files for SCORM

- `lms/page_renderers.py`: SCORMRenderer class
- `lms/lms/api.py`: `upsert_chapter()` with SCORM handling
- `lms/lms/doctype/course_chapter/course_chapter.json`: SCORM fields

> **Note**: Plain video content (like the GCSE videos) should NOT use SCORM. SCORM is for interactive content packages with JavaScript runtime tracking.

---

## API Reference

### Creating Documents Programmatically

```python
import frappe

# Create course
course = frappe.new_doc("LMS Course")
course.title = "My Course"
course.short_introduction = "Brief description"
course.description = "<p>Full description</p>"
course.append("instructors", {"instructor": "Administrator"})
course.insert(ignore_permissions=True)

# Create chapter
chapter = frappe.new_doc("Course Chapter")
chapter.title = "Chapter 1"
chapter.course = course.name
chapter.insert(ignore_permissions=True)

# Create lesson
lesson = frappe.new_doc("Course Lesson")
lesson.title = "Lesson 1"
lesson.chapter = chapter.name
lesson.body = '{{ Video("https://example.com/video.mp4") }}'
lesson.insert(ignore_permissions=True)

# Link with references
frappe.get_doc({
    "doctype": "Chapter Reference",
    "chapter": chapter.name,
    "idx": 1,
    "parent": course.name,
    "parenttype": "LMS Course",
    "parentfield": "chapters"
}).insert(ignore_permissions=True)

frappe.db.commit()
```

### Whitelisted API Methods

From `lms/lms/api.py`:

- `upsert_chapter(title, course, is_scorm_package, scorm_package, name=None)`
- `add_lesson(title, chapter, course, idx)`
- `delete_course(course)`
- `delete_chapter(chapter)`
- `delete_lesson(lesson, chapter)`

---

## Related Documentation

- [Frappe LMS GitHub](https://github.com/frappe/lms)
- [Frappe Framework Docs](https://frappeframework.com/docs)
- [EditorJS Documentation](https://editorjs.io/)
