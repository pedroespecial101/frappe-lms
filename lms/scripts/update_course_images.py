"""
Script to apply cover images to each module course in Frappe LMS.

Images are stored in lms/public/images/courses/ and served via /assets/lms/images/courses/.

Run with:
    bench --site lms.localhost execute lms.scripts.update_course_images.update_course_images
"""
import frappe


def update_course_images():
    # Mapping of Course Title -> image filename (in lms/public/images/courses/)
    course_image_map = {
        "Intro":                                    "course_intro.png",
        "Course Overview":                          "course_overview.png",
        "Exam Technique":                           "course_exam_technique.png",
        "Casio FX-991CW":                           "course_casio_fx991cw.png",
        "Casio FX-991EX":                           "course_casio_fx991ex.png",
        "1 - Number":                               "course_number.png",
        "2 - Algebra":                              "course_algebra.png",
        "3 - Graphs":                               "course_graphs.png",
        "4 - Ratio, Proportion & Rates of Change":  "course_ratio.png",
        "5 - Geometry & Measures":                  "course_geometry.png",
        "6 - Pythagoras, Trigonometry & Vectors":   "course_pythagoras.png",
        "7 - Probability & Statistics":             "course_probability.png",
    }

    print("Starting course image update...")

    courses = frappe.get_all("LMS Course", fields=["name", "title"])

    updated = 0
    skipped = 0

    for course in courses:
        title = course["title"]
        image_file = course_image_map.get(title)

        if not image_file:
            print(f"  ⚠️  No image mapping for course: '{title}' — skipping")
            skipped += 1
            continue

        # Images are in lms/public/images/courses/ → served as /assets/lms/images/courses/
        file_url = f"/assets/lms/images/courses/{image_file}"

        print(f"  Updating '{title}' → {file_url}")
        frappe.db.set_value("LMS Course", course["name"], "image", file_url)
        updated += 1

    frappe.db.commit()
    print(f"\n✅ Done. Updated: {updated}, Skipped: {skipped}")


if __name__ == "__main__":
    update_course_images()
