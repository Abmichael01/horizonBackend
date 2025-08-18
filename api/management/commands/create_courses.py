from django.core.management.base import BaseCommand
from api.models import Department, Course, Semester

class Command(BaseCommand):
    help = 'Delete all previous courses and create 10 new courses for each department, linking them to the two semesters.'

    def handle(self, *args, **kwargs):
        try:
            spring_semester = Semester.objects.get(name="First Semester") 
            fall_semester = Semester.objects.get(name="Second Semester")   
        except Semester.DoesNotExist:
            self.stdout.write(self.style.ERROR("One or both semesters do not exist. Please create them first."))
            return

        # Delete all previously created courses
        Course.objects.all().delete()
        self.stdout.write(self.style.SUCCESS("Successfully deleted all previous courses"))

        # Loop through each department and create 10 courses for each semester
        departments = Department.objects.all()

        for department in departments:
            # Create 10 courses for Spring semester
            for i in range(1, 11):
                course_code = f"{department.short}{i:03d}"  # Generate course code, e.g., "MEE001", "MEE002"
                course_title = f"{department.short} Course {i}"  # Generate course title, e.g., "MEE Course 1"
                course_units = 3  # Example fixed unit for all courses

                # Create course and link to Spring semester
                course, created = Course.objects.get_or_create(
                    code=course_code,
                    title=course_title,
                    units=course_units,
                    department=department,
                    semester=spring_semester  # Link to Spring semester
                )
                if created:
                    self.stdout.write(self.style.SUCCESS(f"Successfully created course: {course_code} - {course_title} (Spring)"))
                else:
                    self.stdout.write(self.style.WARNING(f"Course {course_code} already exists. Skipping..."))

            # Create 10 courses for Fall semester
            for i in range(1, 11):
                course_code = f"{department.short}{i+10:03d}"  # Generate course code, e.g., "MEE011", "MEE012"
                course_title = f"{department.short} Course {i+10}"  # Generate course title, e.g., "MEE Course 11"
                course_units = 3  # Example fixed unit for all courses

                # Create course and link to Fall semester
                course, created = Course.objects.get_or_create(
                    code=course_code,
                    title=course_title,
                    units=course_units,
                    department=department,
                    semester=fall_semester  # Link to Fall semester
                )
                if created:
                    self.stdout.write(self.style.SUCCESS(f"Successfully created course: {course_code} - {course_title} (Fall)"))
                else:
                    self.stdout.write(self.style.WARNING(f"Course {course_code} already exists. Skipping..."))
