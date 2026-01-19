"""
Import script to load GCSE Video Vault modules as separate courses in Frappe LMS.

This script reads the combined_modules_withLocalURL.json file and creates:
- A separate LMS Course for EACH module in the JSON.
- A single "Videos" chapter for each course.
- Course Lessons for each video within that chapter.
- File documents for local assets (using direct SQL to bypass size limits).

Run with: bench --site [sitename] execute lms.scripts.import_modules_as_courses.run_import
"""

import json
import frappe
from frappe import _
import os


def run_import():
    """Main import function."""
    
    # Path to JSON data
    json_path = frappe.get_app_path("lms", "..", "templates", "combined_modules_withLocalURL.json")
    
    print(f"Loading data from: {json_path}")
    
    with open(json_path, 'r') as f:
        modules = json.load(f)
    
    print(f"Found {len(modules)} modules. creating {len(modules)} courses...")
    
    # Sort modules by module_number DESCENDING so they are created in reverse order.
    # Since LMS Course default sort is 'creation desc' (newest first), creating 
    # the last module first ensures it ends up at the bottom of the list.
    sorted_modules = sorted(modules, key=lambda x: float(x.get('module_number', 0)), reverse=True)
    
    created_courses = []

    for idx, module in enumerate(sorted_modules, start=1):
        course = create_course_from_module(module, idx)
        created_courses.append(course.name)
        print(f"Created course {idx}/{len(modules)}: {course.title} ({course.name})")

    frappe.db.commit()
    print(f"\n✅ Import complete! Created {len(created_courses)} courses.")
    for c in created_courses:
        print(f" - {c}")


def create_course_from_module(module_data, idx):
    """Create a full LMS Course for a single module."""
    
    module_name = module_data.get('module_name', f'Module {idx}')
    
    # Check if course already exists and delete it to ensure clean slate
    existing_course = frappe.db.exists("LMS Course", {"title": module_name})
    if existing_course:
        print(f"  Deleting existing course: {module_name}")
        delete_course(existing_course)

    # 1. Create Course
    course = frappe.new_doc("LMS Course")
    course.title = module_name
    course.short_introduction = f"GCSE Mathematics module covering {module_name}."
    course.description = f"""
    <h3>{module_name}</h3>
    <p>This course covers the topic of {module_name} as part of the GCSE Video Vault.</p>
    """
    course.published = 1 
    course.featured = 1 # Make them all featured for now so they show up
    
    # Add Administrator as default instructor
    course.append("instructors", {
        "instructor": "Administrator"
    })
    
    course.insert(ignore_permissions=True)

    # 2. Create Single Chapter (we'll just call it "Videos" or reuse the module name)
    chapter = frappe.new_doc("Course Chapter")
    chapter.title = "Videos" 
    chapter.course = course.name
    chapter.insert(ignore_permissions=True)
    
    # Link chapter to course
    chapter_ref = frappe.new_doc("Chapter Reference")
    chapter_ref.chapter = chapter.name
    chapter_ref.idx = 1
    chapter_ref.parent = course.name
    chapter_ref.parenttype = "LMS Course"
    chapter_ref.parentfield = "chapters"
    chapter_ref.insert(ignore_permissions=True)

    # 3. Create Videos
    videos = sorted(module_data.get('videos', []), key=lambda x: x.get('video_number', 0))
    
    for v_idx, video in enumerate(videos, start=1):
        create_lesson(course, chapter, video, v_idx)

    
    return course


def delete_course(course_name):
    """Delete an existing course and all its related documents."""
    
    # Get all chapters
    chapters = frappe.get_all("Course Chapter", filters={"course": course_name}, pluck="name")
    
    for chapter_name in chapters:
        # Get all lessons in this chapter
        lessons = frappe.get_all("Course Lesson", filters={"chapter": chapter_name}, pluck="name")
        
        # Delete lesson references
        frappe.db.delete("Lesson Reference", {"parent": chapter_name})
        
        # Delete lessons
        for lesson_name in lessons:
            frappe.delete_doc("Course Lesson", lesson_name, force=True)
        
        # Delete chapter reference
        frappe.db.delete("Chapter Reference", {"chapter": chapter_name})
        
        # Delete chapter
        frappe.delete_doc("Course Chapter", chapter_name, force=True)
    
    # Delete the course
    frappe.delete_doc("LMS Course", course_name, force=True)


def ensure_file_record(filename, file_url):
    """Ensure a File document exists for the given filename and URL."""
    if not frappe.db.exists("File", {"file_url": file_url}):
        # Direct DB insertion to bypass file size checks
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


def create_lesson(course, chapter, video_data, idx):
    """Create a Course Lesson from video data."""
    
    # Prioritize local path logic
    original_path = video_data.get('local_path', '')
    video_path = ""
    
    if original_path:
        # Extract filename (handle both simple filenames and paths like mathmo_assets/foo.mp4)
        filename = os.path.basename(original_path)
        video_path = f"/files/{filename}"
        
        # Ensure the File record exists in the database
        ensure_file_record(filename, video_path)
    
    # Fallback to direct URL if local path resolution failed or wasn't provided
    if not video_path:
        video_path = video_data.get('video_direct_url', '')

    # Build the lesson body with video macro
    body_parts = []
    
    # Add video using the Video macro
    if video_path:
        body_parts.append(f'{{{{ Video("{video_path}") }}}}')
    
    # Add subtitle as description if present
    subtitle = video_data.get('subtitle', '')
    if subtitle:
        body_parts.append(f"\n\n{subtitle}")
    
    # Create content in EditorJS format for the new editor
    content_blocks = {
        "time": 1705676400000,
        "blocks": [
            {
                "type": "upload",
                "data": {
                    "file_url": video_path,
                    "file_type": "mp4"
                }
            }
        ],
        "version": "2.28.2"
    }
    
    lesson = frappe.new_doc("Course Lesson")
    lesson.title = video_data.get('title', f'Lesson {idx}')
    lesson.chapter = chapter.name
    lesson.course = course.name
    lesson.body = '\n'.join(body_parts)
    lesson.content = json.dumps(content_blocks)
    lesson.include_in_preview = 1 if idx == 1 else 0  # First lesson is preview
    lesson.insert(ignore_permissions=True)
    
    # Add lesson reference to chapter
    lesson_ref = frappe.new_doc("Lesson Reference")
    lesson_ref.lesson = lesson.name
    lesson_ref.idx = idx
    lesson_ref.parent = chapter.name
    lesson_ref.parenttype = "Course Chapter"
    lesson_ref.parentfield = "lessons"
    lesson_ref.insert(ignore_permissions=True)
    
    return lesson

if __name__ == "__main__":
    run_import()
