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

#### `create_course()`
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
- Uses `video_direct_url` for video embedding (Wistia CDN URLs)
- Falls back to local path if no direct URL
- Creates both `body` (markdown macro) and `content` (EditorJS JSON)
- Creates Lesson Reference for ordering

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
| `videos[].video_direct_url` | string | Direct MP4 URL (preferred) |
| `videos[].local_path` | string | Path to local video file |
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
| `video_direct_url` | Course Lesson | `body` (via Video macro) |
| `video_direct_url` | Course Lesson | `content` (EditorJS format) |
| `video_number` | Lesson Reference | `idx` (ordering) |
| (parent chapter) | Course Lesson | `chapter` |

---

## Video Embedding Options

Frappe LMS supports multiple methods for embedding video content:

### 1. YouTube Field
The `youtube` field on Course Lesson accepts YouTube URLs:
```
https://www.youtube.com/watch?v=VIDEO_ID
```

### 2. Markdown Macros (Body Field)
The `body` field supports markdown with special macros:

```markdown
{{ YouTubeVideo("VIDEO_ID") }}
{{ Video("/path/to/video.mp4") }}
{{ Audio("/path/to/audio.mp3") }}
{{ PDF("/path/to/document.pdf") }}
{{ Quiz("quiz-name") }}
```

Macro renderers are defined in `lms/hooks.py`:
```python
lms_markdown_macro_renderers = {
    "YouTubeVideo": "lms.plugins.youtube_video_renderer",
    "Video": "lms.plugins.video_renderer",
    "Audio": "lms.plugins.audio_renderer",
    "PDF": "lms.plugins.pdf_renderer",
    "Quiz": "lms.plugins.quiz_renderer",
}
```

### 3. EditorJS Content (Content Field)
The newer `content` field uses EditorJS JSON format:

```json
{
  "time": 1705676400000,
  "blocks": [
    {
      "type": "upload",
      "data": {
        "file_url": "https://example.com/video.mp4",
        "file_type": "mp4"
      }
    }
  ],
  "version": "2.28.2"
}
```

### Video URL Options

1. **Direct CDN URLs** (Recommended for external content):
   ```
   https://embed-ssl.wistia.com/deliveries/xxx.mp4
   ```

2. **Local Files** (Requires file serving setup):
   ```
   /files/video.mp4
   ```
   Files must be in: `sites/[site-name]/public/files/`

3. **Frappe File Documents**:
   Upload via Frappe's file upload and use the returned URL.

---

## Running the Import

### Prerequisites

1. Frappe Bench installed and running
2. LMS app installed on the site
3. Source JSON file in place

### Command

From the bench directory:
```bash
bench --site [site-name] execute lms.scripts.import_gcse_course.run_import
```

For this project:
```bash
cd /path/to/lms-bench
bench --site lms.localhost execute lms.scripts.import_gcse_course.run_import
```

### After Import

1. Visit `/lms/courses/[course-slug]` to view the course
2. Check the Frappe desk for course management
3. Test video playback in lessons

---

## Troubleshooting

### Common Issues

#### Videos Not Playing

**Symptom**: Video player shows but video doesn't load

**Solutions**:
1. Use direct CDN URLs (`video_direct_url`) instead of local paths
2. For local files, ensure they're in `sites/[site]/public/files/`
3. Check browser console for 404 errors
4. Verify CORS headers if using external URLs

#### Import Fails with "instructors" Error

**Symptom**: `MandatoryError: instructors`

**Solution**: The `instructors` field is required. Add at least one:
```python
course.append("instructors", {"instructor": "Administrator"})
```

#### Module Not Found

**Symptom**: `ModuleNotFoundError: No module named 'lms.scripts'`

**Solution**: Ensure `__init__.py` exists in `lms/scripts/` and script is in the bench's apps directory (not just the development directory).

### File Locations

```
Development Directory (your code):
/Users/.../frappe-lms/lms/scripts/import_gcse_course.py

Bench Apps Directory (where Frappe looks):
/Users/.../lms-bench/apps/lms/lms/scripts/import_gcse_course.py

Copy script after changes:
cp lms/scripts/*.py ../lms-bench/apps/lms/lms/scripts/
```

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
