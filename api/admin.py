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