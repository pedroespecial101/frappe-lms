import frappe
import os

def check_file_exists(file_path):
    return os.path.exists(file_path)

def update_course_images():
    # Mapping of Course Name (or part of it) to Image File Name
    # Using specific course names from the JSON/DB
    course_image_map = {
        "Intro": "course_intro_1768930969875.png",
        "Course Overview": "course_overview_1768930993180.png",
        "Exam Technique": "course_exam_technique_1768931015389.png",
        "Casio FX-991CW": "course_casio_fx991cw_1768931036232.png",
        "Casio FX-991EX": "course_casio_fx991ex_1768931061636.png",
        "1 - Number": "course_number_1768931098183.png",
        "2 - Algebra": "course_algebra_1768931124085.png",
        "3 - Graphs": "course_graphs_1768931148430.png",
        "4 - Ratio, Proportion & Rates of Change": "course_ratio_1768931170647.png",
        "5 - Geometry & Measures": "course_geometry_1768931247779.png",
        "6 - Pythagoras, Trigonometry & Vectors": "course_pythagoras_1768931269621.png",
        "7 - Probability & Statistics": "course_probability_1768931291179.png"
    }

    print("Starting course image update...")
    
    courses = frappe.get_all("LMS Course", fields=["name", "title"])
    
    for course in courses:
        title = course['title']
        image_file = course_image_map.get(title)
        
        if image_file:
            print(f"Updating '{title}' with image '{image_file}'")
            
            # Construct the file URL (assuming it's in public/files)
            file_url = f"/files/{image_file}"
            
            # Check if the file is accessible (optional, but good practice)
            # In a real scenario, we might want to check the physical path, 
            # but here we trust our previous copy command.
            
            # Update the course record
            frappe.db.set_value("LMS Course", course['name'], "image", file_url)
            
            # Ensure a File document exists for this image (best practice in Frappe)
            # Using raw SQL to avoid permission/size checks if necessary, or just standard ORM
            # Since these are small PNgs, standard ORM is fine if we wanted to register them,
            # but simply setting the URL often works if the file is in public/files.
            # However, for the image to show up in the File Manager, we should register it.
            
            file_exists_in_db = frappe.db.exists("File", {"file_url": file_url})
            if not file_exists_in_db:
                print(f"Creating File record for {image_file}")
                file_doc = frappe.get_doc({
                    "doctype": "File",
                    "file_name": image_file,
                    "file_url": file_url,
                    "is_private": 0,
                    "folder": "Home" # Or "Course Images" if it exists
                })
                try:
                    file_doc.insert(ignore_permissions=True)
                except Exception as e:
                    print(f"Warning: Could not create File record for {image_file}. Error: {e}")
                    # If it fails (e.g. file missing on disk check), we still set the URL on the course
                    pass

        else:
            print(f"No image mapping found for course: '{title}'")

    frappe.db.commit()
    print("Course image update completed.")

if __name__ == "__main__":
    update_course_images()
