from django.urls import path, include
from .views import *

urlpatterns = [
    path("", include('dj_rest_auth.urls')),
    
    # User Registration
    path("auth/create-user/", CreateUserView.as_view(), name="create_user"),
    
    # Student
    path("student/overview/", StudentOverview.as_view()),
    path("student/register-courses/", RegisterCourses.as_view()),
    path("student/registered-courses/", GetRegisteredCourses.as_view()),
    path("student/lms-overview/", StudentLmsOverview.as_view()),
    path("student/assignments/", StudentAssignments.as_view()),
    path("student/grades/", StudentGrades.as_view()),
    path("student/announcements/", StudentAnnouncements.as_view()),
    path("student/course/<int:course_id>/", StudentCourseDetails.as_view()),
    path("student/assignment/<int:assignment_id>/", StudentAssignmentDetails.as_view()),
    path("student/assignment/<int:assignment_id>/submit/", SubmitAssignment.as_view()),
    
    # Lecturer
    path("lecturer/overview/", LecturerOverview.as_view()),
    path("lecturer/lms-overview/", LmsOverview.as_view()),
    path("lecturer/assignments/", AllAssignments.as_view()),
    path("lecturer/course/<int:course_id>/", CourseManagement.as_view()),
    path("lecturer/course/<int:course_id>/assignments/", CourseAssignments.as_view()),
    path("lecturer/course/<int:course_id>/assignments/<int:assignment_id>/", AssignmentDetail.as_view()),
    path("lecturer/course/<int:course_id>/students/", CourseStudents.as_view()),
    path("lecturer/course/<int:course_id>/announcements/", CourseAnnouncements.as_view()),
    path("lecturer/announcements/", GeneralAnnouncements.as_view()),
]