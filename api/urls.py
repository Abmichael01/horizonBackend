from django.urls import path, include
from .views_student import *
from .views import CreateUserView

urlpatterns = [
    path("", include('dj_rest_auth.urls')),
    
    # User Registration
    path("auth/create-user/", CreateUserView.as_view(), name="create_user"),
    
    # Student
    path("student/overview/", StudentOverview.as_view()),
    path("student/register-courses/", RegisterCourses.as_view()),
    path("student/registered-courses/", GetRegisteredCourses.as_view()),
]