"""
Import script to load GCSE Video Vault course data into Frappe LMS.

This script reads the combined_modules_withLocalURL.json file and creates:
- One LMS Course
- Course Chapters for each module
- Course Lessons for each video

Run with: bench --site [sitename] execute lms.scripts.import_gcse_course.run_import
"""

import json
import frappe
from frappe import _


def run_import():
    """Main import function."""
    
    # Path to JSON data
    json_path = frappe.get_app_path("lms", "..", "templates", "combined_modules_withLocalURL.json")
    
    print(f"Loading data from: {json_path}")
    
    with open(json_path, 'r') as f:
        modules = json.load(f)
    
    print(f"Found {len(modules)} modules to import")
    
    # Check if course already exists
    existing_course = frappe.db.exists("LMS Course", {"title": "GCSE Video Vault"})
    if existing_course:
        print(f"Course 'GCSE Video Vault' already exists: {existing_course}")
        print("Deleting existing course to re-import...")
        delete_course(existing_course)
    
    # Create the main course
    course = create_course()
    print(f"Created course: {course.name}")
    
    # Sort modules by module_number
    sorted_modules = sorted(modules, key=lambda x: float(x.get('module_number', 0)))
    
    # Create chapters and lessons
    for idx, module in enumerate(sorted_modules, start=1):
        chapter = create_chapter(course, module, idx)
        print(f"  Created chapter {idx}: {chapter.title}")
        
        # Sort videos by video_number
        sorted_videos = sorted(module.get('videos', []), key=lambda x: x.get('video_number', 0))
        
        for lesson_idx, video in enumerate(sorted_videos, start=1):
            lesson = create_lesson(course, chapter, video, lesson_idx)
            print(f"    Created lesson {lesson_idx}: {lesson.title}")
    
    # Publish the course
    course.reload()
    course.published = 1
    course.save()
    
    frappe.db.commit()
    print(f"\n✅ Import complete! Course '{course.title}' created with {len(sorted_modules)} chapters.")
    print(f"   View at: /lms/courses/{course.name}")
    
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
    frappe.db.commit()
    print(f"Deleted existing course: {course_name}")


def create_course():
    """Create the main LMS Course document."""
    
    course = frappe.new_doc("LMS Course")
    course.title = "GCSE Video Vault"
    course.short_introduction = "Complete GCSE Mathematics video course covering all topics from basics to advanced problem-solving techniques."
    course.description = """
<h3>Welcome to the GCSE Video Vault</h3>
<p>This comprehensive course covers everything you need to succeed in your GCSE Mathematics exam.</p>

<h4>What's Included:</h4>
<ul>
    <li>Complete topic coverage from Foundation to Higher tier</li>
    <li>Exam technique videos and strategies</li>
    <li>Calculator tutorials (Casio FX-991CW and FX-991EX)</li>
    <li>Step-by-step worked examples</li>
</ul>

<p>Work through the modules at your own pace and revisit any topic as many times as you need.</p>
"""
    course.published = 0  # Will publish after import
    course.featured = 1
    
    # Add Administrator as default instructor (required field)
    course.append("instructors", {
        "instructor": "Administrator"
    })
    
    course.insert(ignore_permissions=True)
    
    return course


def create_chapter(course, module_data, idx):
    """Create a Course Chapter from module data."""
    
    chapter = frappe.new_doc("Course Chapter")
    chapter.title = module_data.get('module_name', f'Module {idx}')
    chapter.course = course.name
    chapter.insert(ignore_permissions=True)
    
    # Add chapter reference to course
    chapter_ref = frappe.new_doc("Chapter Reference")
    chapter_ref.chapter = chapter.name
    chapter_ref.idx = idx
    chapter_ref.parent = course.name
    chapter_ref.parenttype = "LMS Course"
    chapter_ref.parentfield = "chapters"
    chapter_ref.insert(ignore_permissions=True)
    
    return chapter


def create_lesson(course, chapter, video_data, idx):
    """Create a Course Lesson from video data."""
    
    # Use the direct Wistia video URL (works immediately, no file serving needed)
    video_path = video_data.get('video_direct_url', '')
    
    # Fallback to local path if no direct URL
    if not video_path:
        original_path = video_data.get('local_path', '')
        if original_path.startswith('mathmo_assets/'):
            video_path = original_path.replace('mathmo_assets/', '/files/')
        else:
            video_path = f"/files/{original_path}"
    
    # Build the lesson body with video macro
    body_parts = []
    
    # Add video using the Video macro
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
    lesson.include_in_preview = 1 if idx == 1 else 0  # First lesson of each chapter is preview
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
