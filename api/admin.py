from django.contrib import admin
from .models import *

@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ('email', 'is_active', 'is_staff', 'date_joined')
    search_fields = ('email',)

@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ('name', 'short', 'faculty', 'get_hod', 'created_at')
    search_fields = ('name', 'short')
    list_filter = ('faculty',)
    ordering = ('name',)
    
    def get_hod(self, obj):
        """Display HOD name"""
        return obj.hod.full_name if obj.hod else "Not assigned"
    get_hod.short_description = 'Head of Department'

@admin.register(StudentProfile)
class StudentProfileAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'matric_number', 'department', 'level', 'cgpa', 'created_at')
    search_fields = ('full_name', 'matric_number')
    list_filter = ('department', 'level')
    ordering = ('matric_number',)
    
@admin.register(AcademicSession)
class AcademicSessionAdmin(admin.ModelAdmin):
    list_display = ('session_name', 'start_date', 'end_date')
    

@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ('code', 'title', 'department', 'semester', 'units', 'level', 'get_assigned_lecturers', 'get_borrowing_departments')
    search_fields = ('code', 'title', 'department__name', 'department__short', 'assigned_lecturers__full_name')
    list_filter = ('department', 'semester', 'units', 'level', 'assigned_lecturers', 'borrowing_departments')
    ordering = ('code',)
    list_per_page = 25
    filter_horizontal = ('assigned_lecturers', 'borrowing_departments')  # Better UI for many-to-many fields
    
    def get_assigned_lecturers(self, obj):
        """Display assigned lecturers in list view"""
        return ", ".join([lecturer.full_name for lecturer in obj.assigned_lecturers.all()])
    get_assigned_lecturers.short_description = 'Assigned Lecturers'
    
    def get_borrowing_departments(self, obj):
        """Display borrowing departments in list view"""
        borrowing = [dept.short for dept in obj.borrowing_departments.all()]
        return ", ".join(borrowing) if borrowing else "None"
    get_borrowing_departments.short_description = 'Borrowing Departments'
    

@admin.register(LecturerProfile)
class LecturerProfileAdmin(admin.ModelAdmin):
    list_display = ('id', 'full_name', 'department', 'specialization', 'get_assigned_courses_count', 'created_at')
    search_fields = ('id', 'full_name', 'department__name', 'department__short')
    list_filter = ('department', 'created_at')
    ordering = ('id',)
    readonly_fields = ('id',)
    
    def get_assigned_courses_count(self, obj):
        """Display number of assigned courses"""
        return obj.assigned_courses.count()
    get_assigned_courses_count.short_description = 'Assigned Courses'

admin.site.register([
    Semester,
    Faculty,
    CourseEnrollment,
    CourseRegistration,
    Level,
])