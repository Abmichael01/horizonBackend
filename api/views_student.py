from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .models.models import *
from .serializers import *
from django.shortcuts import get_object_or_404
from django.db import transaction
from django.db.models import Q

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


class RegisterCourses(APIView):
    def get(self, request, *args, **kwargs):
        current_semester = Semester.objects.filter(is_current=True).first()
        
        if not current_semester:
            return Response({"detail": "No current semester set."}, status=status.HTTP_404_NOT_FOUND)
        
        student_profile = get_object_or_404(StudentProfile, user=request.user.id)
        departmental_courses = Course.objects.filter(semester=current_semester, department=student_profile.department)
        
        # Get all courses the student has already registered for this semester
        registered_course_ids = set(
            CourseRegistration.objects.filter(
                student=student_profile,
                semester=current_semester
            ).values_list('courses__course__id', flat=True)
        )
        
        # Check if student has registered all departmental courses
        all_dept_course_ids = set(departmental_courses.values_list('id', flat=True))
        has_registered_all_dept_courses = all_dept_course_ids.issubset(registered_course_ids) and all_dept_course_ids

        # Check if 'search' parameter is provided
        search = request.GET.get('search', None)
        if search is not None and search != "":
            # Search for any course in the current semester, excluding already registered ones
            courses = Course.objects.filter(
                semester=current_semester
            ).filter(
                Q(code__icontains=search) | Q(title__icontains=search)
            ).exclude(id__in=registered_course_ids)
            serializer = CourseSerializer(courses, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        elif has_registered_all_dept_courses:
            # No search, but all departmental courses registered: prompt to search for borrowed courses
            return Response([], status=status.HTTP_200_OK)
        else:
            # Not all departmental courses registered, show unregistered departmental courses only
            courses = departmental_courses.exclude(id__in=registered_course_ids)
            serializer = CourseSerializer(courses, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
    
    def post(self, request, *args, **kwargs):
        # Get course codes from request data
        course_codes = request.data.get('course_codes', [])
        
        if not course_codes:
            return Response(
                {"detail": "No course codes provided."}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Get current semester and session
        current_semester = Semester.objects.filter(is_current=True).first()
        current_session = AcademicSession.objects.filter(is_current=True).first()
        
        if not current_semester:
            return Response(
                {"detail": "No current semester set."}, 
                status=status.HTTP_404_NOT_FOUND
            )
        
        if not current_session:
            return Response(
                {"detail": "No current academic session set."}, 
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Get student profile
        student_profile = get_object_or_404(StudentProfile, user=request.user.id)
        
        # Check if student already has a registration for current semester/session
        existing_registration = CourseRegistration.objects.filter(
            student=student_profile,
            academic_session=current_session,
            semester=current_semester
        ).first()
        
        # Validate course codes
        # Allow any course in the current semester, regardless of department
        courses = Course.objects.filter(
            code__in=course_codes, 
            semester=current_semester
        )
        
        if len(courses) != len(course_codes):
            found_codes = list(courses.values_list('code', flat=True))
            invalid_codes = [code for code in course_codes if code not in found_codes]
            return Response(
                {
                    "detail": f"Invalid course codes: {', '.join(invalid_codes)}"
                }, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            with transaction.atomic():
                if existing_registration:
                    # Get codes of already registered courses
                    already_registered_codes = set(
                        existing_registration.courses.all().values_list('course__code', flat=True)
                    )
                    # Only add new courses not already registered
                    new_courses = [course for course in courses if course.code not in already_registered_codes]
                    if not new_courses:
                        return Response(
                            {"detail": "All provided courses are already registered."},
                            status=status.HTTP_400_BAD_REQUEST
                        )
                    new_enrollments = []
                    for course in new_courses:
                        enrollment = CourseEnrollment.objects.create(
                            student=student_profile,
                            course=course,
                            grade='',  # Empty initially, will be filled when grades are available
                            grade_point=0.0,  # 0 initially
                            academic_session=current_session,
                            semester=current_semester
                        )
                        new_enrollments.append(enrollment)
                    # Add new enrollments to the registration
                    existing_registration.courses.add(*new_enrollments)
                    # Update total_units
                    existing_registration.total_units += sum(course.units for course in new_courses)
                    existing_registration.save()
                    return Response(
                        {
                            "detail": "New courses added to your registration.",
                            "added_courses": [course.code for course in new_courses],
                            "total_units": existing_registration.total_units
                        },
                        status=status.HTTP_200_OK
                    )
                else:
                    # Create CourseEnrollment for each course (without grades initially)
                    course_enrollments = []
                    for course in courses:
                        enrollment = CourseEnrollment.objects.create(
                            student=student_profile,
                            course=course,
                            grade='',  # Empty initially, will be filled when grades are available
                            grade_point=0.0,  # 0 initially
                            academic_session=current_session,
                            semester=current_semester
                        )
                        course_enrollments.append(enrollment)
                    
                    # Create CourseRegistration and link all enrollments
                    registration = CourseRegistration.objects.create(
                        student=student_profile,
                        academic_session=current_session,
                        semester=current_semester,
                        total_units=sum(course.units for course in courses)
                    )
                    
                    # Add all enrollments to the registration
                    registration.courses.set(course_enrollments)
                    
                    return Response(
                        {
                            "detail": "Courses registered successfully.",
                            "registered_courses": list(courses.values_list('code', flat=True)),
                            "total_units": registration.total_units
                        }, 
                        status=status.HTTP_201_CREATED
                    )
        except Exception as e:
            return Response(
                {"detail": f"Registration failed: {str(e)}"}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class GetRegisteredCourses(APIView):
    """
    View to get the student's registered courses for the current semester.
    Returns total course count, total units, and course details.
    """
    def get(self, request, *args, **kwargs):
        try:
            # Get current semester and session
            current_semester = Semester.objects.filter(is_current=True).first()
            current_session = AcademicSession.objects.filter(is_current=True).first()
            
            if not current_semester:
                return Response(
                    {"detail": "No current semester set."}, 
                    status=status.HTTP_404_NOT_FOUND
                )
            
            if not current_session:
                return Response(
                    {"detail": "No current academic session set."}, 
                    status=status.HTTP_404_NOT_FOUND
                )
            
            # Get student profile
            student_profile = get_object_or_404(StudentProfile, user=request.user.id)
            
            # Get the student's registration for current semester/session
            registration = CourseRegistration.objects.filter(
                student=student_profile,
                academic_session=current_session,
                semester=current_semester
            ).first()
            
            if not registration:
                return Response({
                    "detail": "No registration found for current semester.",
                    "total_courses": 0,
                    "total_units": 0,
                    "courses": []
                }, status=status.HTTP_200_OK)
            
            # Get all course enrollments for this registration
            course_enrollments = registration.courses.all()
            
            # Get the Course objects from the enrollments
            courses = [enrollment.course for enrollment in course_enrollments]
            
            # Serialize the Course objects
            course_serializer = CourseSerializer(courses, many=True)
            
            # Calculate totals
            total_courses = len(courses)
            total_units = registration.total_units
            
            return Response({
                "total_courses": total_courses,
                "total_units": total_units,
                "courses": course_serializer.data,
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response(
                {"detail": f"Error retrieving registered courses: {str(e)}"}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )