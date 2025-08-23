from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.utils import timezone


class UserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("The email is required")
        
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)

        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")

        return self.create_user(email, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    email = models.EmailField(unique=True)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    date_joined = models.DateTimeField(auto_now_add=True)
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                       
    objects = UserManager()

    USERNAME_FIELD = 'email'  # Email will be the unique identifier for login
    REQUIRED_FIELDS = []  # No need for username, only email is required

    def __str__(self):
        return self.email


class AcademicSession(models.Model):
    session_name = models.CharField(max_length=255)  # E.g., "Fall 2025", "Spring 2025"
    start_date = models.DateField()  # Start date of the academic session
    end_date = models.DateField()  # End date of the academic session
    is_current = models.BooleanField(default=False)  # Mark if session is the current active session

    def save(self, *args, **kwargs):
        # Ensure only one session is "current" at a time
        if self.is_current:
            # Set all other sessions to not be current
            AcademicSession.objects.exclude(id=self.id).update(is_current=False)
        
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.session_name} (Current: {self.is_current})"

    class Meta:
        ordering = ['-start_date'] 


class Faculty(models.Model):
    name = models.CharField(max_length=100, unique=True)  # Name of the Faculty (e.g., "Engineering")
    created_at = models.DateTimeField(auto_now_add=True)  # Date the faculty was created
    short = models.CharField(max_length=3, unique=True, null=True)

    def __str__(self):
        return self.name

class Department(models.Model):
    name = models.CharField(max_length=100, unique=True)
    short = models.CharField(max_length=3, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    faculty = models.ForeignKey(Faculty, related_name='departments', on_delete=models.CASCADE, null=True)

    def __str__(self):
        return self.name


class Level(models.Model):
    """
    Represents a student/class level, e.g., 100, 200, 300, etc.
    """
    name = models.PositiveIntegerField(unique=True)  # e.g., 100, 200, 300

    def __str__(self):
        return f"{self.name} Level"


class StudentProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='student_profile')
    full_name = models.CharField(max_length=100)
    matric_number = models.CharField(max_length=20, unique=True)
    dob = models.DateField(verbose_name='Date of Birth')
    cgpa = models.DecimalField(max_digits=4, decimal_places=2, null=True, blank=True)
    phone = models.CharField(max_length=20, blank=True)      
    department = models.ForeignKey(Department, on_delete=models.SET_NULL, null=True, blank=True)
    level = models.ForeignKey(Level, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.full_name} ({self.matric_number})"

class Semester(models.Model):
    name = models.CharField(max_length=255)  # Admin can name the semester (e.g., "Fall 2025")
    is_current = models.BooleanField(default=False)  # Mark the current active semester

    class Meta:
        ordering = ['-name']  # Order semesters by name (e.g., to have the most recent ones first)

    def __str__(self):
        return f"{self.name} (Current: {self.is_current})"

    def save(self, *args, **kwargs):
        # Ensure only one semester is marked as current
        if self.is_current:
            # Set all other semesters to not be current
            Semester.objects.exclude(id=self.id).update(is_current=False)
        
        super().save(*args, **kwargs)

class Course(models.Model):
    code = models.CharField(max_length=10, unique=True)  # Unique code for the course, e.g., "CS101"
    title = models.CharField(max_length=255)  # Title of the course, e.g., "Introduction to Computer Science"
    units = models.PositiveIntegerField()  # Units of the course (e.g., 3 units)
    department = models.ForeignKey(
        Department, 
        related_name='courses', 
        on_delete=models.CASCADE
    )  # Link the course to a department
    semester = models.ForeignKey(
        Semester, 
        related_name='courses', 
        on_delete=models.CASCADE,
        null=True
    )  # Link the course to a semester
    level = models.ForeignKey(
        Level,
        related_name='courses',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text="Level for which this course is intended (e.g., 100, 200, etc.)"
    )  # Link the course to a level
    
    def __str__(self):
        return f"{self.code} - {self.title}"

    class Meta:
        ordering = ['code']  # Order courses by their code
        
class CourseEnrollment(models.Model):
    student = models.ForeignKey(
        StudentProfile, 
        on_delete=models.CASCADE, 
        related_name='course_enrollments'
    )
    course = models.ForeignKey(
        Course, 
        on_delete=models.CASCADE, 
        related_name='course_enrollments'
    )
    grade = models.CharField(max_length=2)  # A, B, C, D, F, etc.
    grade_point = models.DecimalField(
        max_digits=3, 
        decimal_places=2
    )  # 4.0, 3.7, etc.
    academic_session = models.ForeignKey(
        AcademicSession,
        on_delete=models.CASCADE,
        related_name='course_enrollments'
    )
    semester = models.ForeignKey(
        Semester,
        on_delete=models.CASCADE,
        related_name='student_results'
    )
    date_recorded = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['student', 'course', 'academic_session', 'semester']
        ordering = ['-date_recorded']
        
    def __str__(self):
        return f"{self.student.full_name} - {self.course.code}: {self.grade}"
    
    @property
    def total_grade_points(self):
        """Calculate total grade points (grade_point * course_units)"""
        return self.grade_point * self.course.units


class CourseRegistration(models.Model):
    student = models.ForeignKey(
        StudentProfile, 
        on_delete=models.CASCADE, 
        related_name='course_registrations'
    )
    academic_session = models.ForeignKey(
        AcademicSession,
        on_delete=models.CASCADE,
        related_name='course_registrations'
    )
    semester = models.ForeignKey(
        Semester,
        on_delete=models.CASCADE,
        related_name='course_registrations'
    )
    courses = models.ManyToManyField(
        CourseEnrollment,
        related_name='course_registrations',
        blank=True
    )
    enrollment_date = models.DateTimeField(auto_now_add=True)
    total_units = models.PositiveIntegerField(default=0)
    semester_gpa = models.DecimalField(
        max_digits=4, 
        decimal_places=2, 
        null=True, 
        blank=True
    )
    
    class Meta:
        unique_together = ['student', 'academic_session', 'semester']
        ordering = ['-enrollment_date']
        
    def __str__(self):
        return f"{self.student.full_name} - {self.academic_session.session_name} {self.semester.name}"