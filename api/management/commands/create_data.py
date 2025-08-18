from django.core.management.base import BaseCommand
from api.models import Faculty, Department
from django.db import IntegrityError

class Command(BaseCommand):
    help = 'Create Faculties and Departments with short names'

    def handle(self, *args, **kwargs):
        # Array of Faculties (name, short)
        faculties_data = [
            {"name": "Faculty of Engineering and Technology", "short": "FET"},
            {"name": "Faculty of Arts and Humanities", "short": "FAH"},
            {"name": "Faculty of Business Administration", "short": "FBA"},
            {"name": "Faculty of Health Sciences", "short": "FHS"},
            {"name": "Faculty of Science", "short": "FS"},
        ]

        # Array of Departments (name, short, assigned to a faculty)
        departments_data = [
            {"name": "Computer Science", "short": "CS", "faculty_name": "Faculty of Engineering and Technology"},
            {"name": "Electrical Engineering", "short": "EEE", "faculty_name": "Faculty of Engineering and Technology"},
            {"name": "Mechanical Engineering", "short": "MEE", "faculty_name": "Faculty of Engineering and Technology"},
            {"name": "English Literature", "short": "ELT", "faculty_name": "Faculty of Arts and Humanities"},
            {"name": "History", "short": "HIS", "faculty_name": "Faculty of Arts and Humanities"},
            {"name": "Marketing", "short": "MKT", "faculty_name": "Faculty of Business Administration"},
            {"name": "Accounting", "short": "ACC", "faculty_name": "Faculty of Business Administration"},
            {"name": "Nursing", "short": "NUR", "faculty_name": "Faculty of Health Sciences"},
            {"name": "Public Health", "short": "PHL", "faculty_name": "Faculty of Health Sciences"},
            {"name": "Physics", "short": "PHY", "faculty_name": "Faculty of Science"},
            {"name": "Chemistry", "short": "CHE", "faculty_name": "Faculty of Science"},
        ]

        # Create Faculties
        for faculty_data in faculties_data:
            # Check if short is exactly 3 characters and unique
            if len(faculty_data["short"]) == 3:
                if Faculty.objects.filter(short=faculty_data["short"]).exists():
                    self.stdout.write(self.style.WARNING(f"Faculty with short {faculty_data['short']} already exists. Skipping..."))
                    continue
                faculty, created = Faculty.objects.get_or_create(
                    name=faculty_data["name"],
                    short=faculty_data["short"]
                )
                if created:
                    self.stdout.write(self.style.SUCCESS(f"Successfully created Faculty: {faculty.name}"))
                else:
                    self.stdout.write(self.style.WARNING(f"Faculty {faculty.name} already exists"))
            else:
                self.stdout.write(self.style.WARNING(f"Faculty short code must be exactly 3 characters. Skipping: {faculty_data['short']}"))

        # Create Departments and link them to Faculties
        for department_data in departments_data:
            # Check if short is exactly 3 characters and unique
            if len(department_data["short"]) == 3:
                if Department.objects.filter(short=department_data["short"]).exists():
                    self.stdout.write(self.style.WARNING(f"Department with short {department_data['short']} already exists. Skipping..."))
                    continue
                
                # Get the Faculty object
                try:
                    faculty = Faculty.objects.get(name=department_data["faculty_name"])  # Get the faculty by name
                except Faculty.DoesNotExist:
                    self.stdout.write(self.style.ERROR(f"Faculty '{department_data['faculty_name']}' not found. Skipping department {department_data['name']}"))
                    continue

                department, created = Department.objects.get_or_create(
                    name=department_data["name"],
                    short=department_data["short"],
                    faculty=faculty  # Associate the department with the faculty
                )

                if created:
                    self.stdout.write(self.style.SUCCESS(f"Successfully created Department: {department.name}"))
                else:
                    self.stdout.write(self.style.WARNING(f"Department {department.name} already exists"))
            else:
                self.stdout.write(self.style.WARNING(f"Department short code must be exactly 3 characters. Skipping: {department_data['short']}"))
