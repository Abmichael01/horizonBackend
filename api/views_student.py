from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .models import *
from .serializers import *
from django.shortcuts import get_object_or_404

class StudentOverview(APIView):
    """
    View that returns the student's profile along with the current academic session.
    """
    def get(self, request, *args, **kwargs):
        try:
            student_profile = StudentProfile.objects.get(user=request.user)
            current_session = AcademicSession.objects.filter(is_current=True).first()
            student_profile_serializer = StudentProfileSerializer(student_profile)
            current_session_serializer = AcademicSessionSerializer(current_session)
            semester = Semester.objects.get(is_current=True)

            return Response({
                'current_semester': semester.name,
                'student_profile': student_profile_serializer.data,
                'current_academic_session': current_session_serializer.data
            }, status=status.HTTP_200_OK)
        
        except StudentProfile.DoesNotExist:
            return Response(
                {'detail': 'Student profile not found.'},
                status=status.HTTP_404_NOT_FOUND
            )
        except AcademicSession.DoesNotExist:
            return Response(
                {'detail': 'No current academic session found.'},
                status=status.HTTP_404_NOT_FOUND
            )


class AvailableCourses(APIView):
    def get(self, request, *args, **kwargs):
        current_semester = Semester.objects.filter(is_current=True).first()
        
        if not current_semester:
            return Response({"detail": "No current semester set."}, status=status.HTTP_404_NOT_FOUND)
        student_profile = get_object_or_404(StudentProfile, user=request.user)
        courses = Course.objects.filter(semester=current_semester, department=student_profile.department)

        # 4. Check if 'search' parameter is provided
        search = request.GET.get('search', None)
        if search:
            # Filter courses by search term in the course code or title
            courses = courses.filter(
                Q(code__icontains=search) | Q(title__icontains=search)
            )

        # 5. Serialize the courses and return the response
        serializer = CourseSerializer(courses, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)