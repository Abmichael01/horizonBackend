from django.contrib import admin
from .models import *

@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ('email', 'is_active', 'is_staff', 'date_joined')
    search_fields = ('email',)

@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ('name', 'short', 'created_at')
    search_fields = ('name', 'short')
    ordering = ('name',)

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
    list_display = ('code', 'title', 'department', 'semester')
    

@admin.register(LecturerProfile)
class LecturerProfileAdmin(admin.ModelAdmin):
    list_display = ('id', 'full_name', 'department', 'specialization', 'created_at')
    search_fields = ('id', 'full_name')
    list_filter = ('department', 'created_at')
    ordering = ('id',)
    readonly_fields = ('id',)

admin.site.register([
    Semester,
    Faculty,
    CourseEnrollment,
    CourseRegistration,
    Level,
])