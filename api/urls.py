from django.urls import path, include
from .views_student import *

urlpatterns = [
    path("", include('dj_rest_auth.urls')),
    
    # Student
    path("student/overview/", StudentOverview.as_view()),
    path("student/available-courses/", AvailableCourses.as_view())
]