from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from ..models import *
from ..serializers import *
from django.shortcuts import get_object_or_404
from django.db import transaction
from django.db.models import Q

def get_student_enrolled_courses(student_profile, current_semester, current_session):
    """
    Helper function to get enrolled courses for a student in current semester/session
    """
    try:
        # First get the course registration for current semester/session
        course_registration = CourseRegistration.objects.filter(
            student=student_profile,
            semester=current_semester,
            academic_session=current_session
        ).first()
        
        if course_registration:
            # Get the CourseEnrollment objects from the registration
            course_enrollments = course_registration.courses.all().select_related('course')
            
            # Extract the Course objects from the CourseEnrollment objects
            course_ids = []
            for enrollment in course_enrollments:
                if enrollment.course:
                    course_ids.append(enrollment.course.id)
            
            enrolled_courses = Course.objects.filter(id__in=course_ids).distinct()
        else:
            enrolled_courses = Course.objects.none()
        
        return enrolled_courses
    except Exception as e:
        print(f"Error in get_student_enrolled_courses: {str(e)}")
        return Course.objects.none()

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
        
        # Get courses for student's department (owned courses + borrowed courses)
        departmental_courses = Course.objects.filter(
            Q(semester=current_semester, department=student_profile.department) |
            Q(semester=current_semester, borrowing_departments=student_profile.department)
        ).distinct()
        
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

class StudentLmsOverview(APIView):
    """
    View that returns student LMS overview with statistics.
    """
    def get(self, request, *args, **kwargs):
        try:
            print(f"StudentLmsOverview - User: {request.user}")
            
            student_profile = StudentProfile.objects.get(user=request.user)
            print(f"StudentLmsOverview - Student Profile: {student_profile}")
            
            current_semester = Semester.objects.filter(is_current=True).first()
            current_session = AcademicSession.objects.filter(is_current=True).first()
            
            print(f"StudentLmsOverview - Semester: {current_semester}, Session: {current_session}")
            
            if not current_semester:
                return Response(
                    {"detail": "No current semester set."}, 
                    status=status.HTTP_404_NOT_FOUND
                )
            
            # Get enrolled courses for current semester
            print("StudentLmsOverview - Getting enrolled courses...")
            enrolled_courses = get_student_enrolled_courses(student_profile, current_semester, current_session)
            print(f"StudentLmsOverview - Enrolled courses count: {enrolled_courses.count()}")
            
            # Calculate statistics
            total_courses = enrolled_courses.count()
            
            # Count pending assignments (not submitted)
            print("StudentLmsOverview - Counting pending assignments...")
            pending_assignments = Assignment.objects.filter(
                course__in=enrolled_courses,
                is_published=True
            ).exclude(
                submissions__student=student_profile,
                submissions__status='submitted'
            ).count()
            print(f"StudentLmsOverview - Pending assignments: {pending_assignments}")
            
            # Count submitted assignments
            print("StudentLmsOverview - Counting submitted assignments...")
            submitted_assignments = AssignmentSubmission.objects.filter(
                student=student_profile,
                status='submitted'
            ).count()
            print(f"StudentLmsOverview - Submitted assignments: {submitted_assignments}")
            
            # Calculate current GPA (mock for now)
            current_gpa = 3.5  # TODO: Calculate from actual grades
            
            # Serialize courses
            print("StudentLmsOverview - Serializing courses...")
            course_serializer = CourseSerializer(enrolled_courses, many=True)
            
            print("StudentLmsOverview - Returning response...")
            return Response({
                'total_courses': total_courses,
                'pending_assignments': pending_assignments,
                'submitted_assignments': submitted_assignments,
                'current_gpa': current_gpa,
                'current_semester': current_semester.name,
                'current_session': current_session.session_name if current_session else None,
                'enrolled_courses': course_serializer.data
            }, status=status.HTTP_200_OK)
            
        except StudentProfile.DoesNotExist:
            print("StudentLmsOverview - Student profile not found")
            return Response(
                {'detail': 'Student profile not found.'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            print(f"StudentLmsOverview - Exception: {str(e)}")
            import traceback
            traceback.print_exc()
            return Response(
                {'detail': f'Error retrieving LMS overview: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class StudentAssignments(APIView):
    """
    View that returns all assignments for enrolled courses with submission status.
    """
    def get(self, request, *args, **kwargs):
        try:
            student_profile = StudentProfile.objects.get(user=request.user)
            current_semester = Semester.objects.filter(is_current=True).first()
            current_session = AcademicSession.objects.filter(is_current=True).first()
            
            if not current_semester:
                return Response(
                    {"detail": "No current semester set."}, 
                    status=status.HTTP_404_NOT_FOUND
                )
            
            # Get enrolled courses
            enrolled_courses = get_student_enrolled_courses(student_profile, current_semester, current_session)
            
            # Get assignments from enrolled courses
            assignments = Assignment.objects.filter(
                course__in=enrolled_courses,
                is_published=True
            ).select_related('course').order_by('-created_at')
            
            # Calculate statistics
            total_assignments = assignments.count()
            pending_assignments = assignments.exclude(
                submissions__student=student_profile,
                submissions__status='submitted'
            ).count()
            submitted_assignments = AssignmentSubmission.objects.filter(
                student=student_profile,
                status='submitted'
            ).count()
            
            # Count overdue assignments
            from django.utils import timezone
            overdue_assignments = assignments.filter(
                due_date__lt=timezone.now()
            ).exclude(
                submissions__student=student_profile,
                submissions__status='submitted'
            ).count()
            
            # Serialize assignments with submission status
            assignment_data = []
            for assignment in assignments:
                submission = AssignmentSubmission.objects.filter(
                    assignment=assignment,
                    student=student_profile
                ).first()
                
                assignment_data.append({
                    'id': assignment.id,
                    'course': CourseSerializer(assignment.course).data,
                    'title': assignment.title,
                    'description': assignment.description,
                    'assignment_type': assignment.assignment_type,
                    'max_points': assignment.max_points,
                    'due_date': assignment.due_date,
                    'created_at': assignment.created_at,
                    'submission_status': submission.status if submission else 'not_started',
                    'due_date_status': 'overdue' if assignment.due_date < timezone.now() else 'upcoming',
                    'submission': submission
                })
            
            return Response({
                'total_assignments': total_assignments,
                'pending_assignments': pending_assignments,
                'submitted_assignments': submitted_assignments,
                'overdue_assignments': overdue_assignments,
                'current_semester': current_semester.name,
                'current_session': current_session.session_name if current_session else None,
                'assignments': assignment_data
            }, status=status.HTTP_200_OK)
            
        except StudentProfile.DoesNotExist:
            return Response(
                {'detail': 'Student profile not found.'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {'detail': f'Error retrieving assignments: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class StudentGrades(APIView):
    """
    View that returns student grades and academic performance.
    """
    def get(self, request, *args, **kwargs):
        try:
            student_profile = StudentProfile.objects.get(user=request.user)
            current_semester = Semester.objects.filter(is_current=True).first()
            current_session = AcademicSession.objects.filter(is_current=True).first()
            
            if not current_semester:
                return Response(
                    {"detail": "No current semester set."}, 
                    status=status.HTTP_404_NOT_FOUND
                )
            
            # Get enrolled courses
            enrolled_courses = get_student_enrolled_courses(student_profile, current_semester, current_session)
            
            # Mock grades data for now - replace with actual grades when available
            grades_data = []
            for course in enrolled_courses:
                grades_data.append({
                    'id': course.id,
                    'course': CourseSerializer(course).data,
                    'grade': 'A',
                    'grade_point': 4.0,
                    'total_points': 100,
                    'earned_points': 95,
                    'feedback': 'Excellent work!',
                    'graded_at': '2024-01-15T10:00:00Z',
                    'semester': current_semester.name,
                    'academic_session': current_session.session_name if current_session else None
                })
            
            # Calculate statistics
            total_courses = enrolled_courses.count()
            current_gpa = 3.5  # Mock GPA
            total_credits = sum(course.units for course in enrolled_courses)
            completed_credits = total_credits  # Mock completed credits
            
            return Response({
                'total_courses': total_courses,
                'current_gpa': current_gpa,
                'total_credits': total_credits,
                'completed_credits': completed_credits,
                'current_semester': current_semester.name,
                'current_session': current_session.session_name if current_session else None,
                'grades': grades_data
            }, status=status.HTTP_200_OK)
            
        except StudentProfile.DoesNotExist:
            return Response(
                {'detail': 'Student profile not found.'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {'detail': f'Error retrieving grades: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class StudentAnnouncements(APIView):
    """
    View that returns course announcements for enrolled courses.
    """
    def get(self, request, *args, **kwargs):
        try:
            student_profile = StudentProfile.objects.get(user=request.user)
            current_semester = Semester.objects.filter(is_current=True).first()
            current_session = AcademicSession.objects.filter(is_current=True).first()
            
            if not current_semester:
                return Response(
                    {"detail": "No current semester set."}, 
                    status=status.HTTP_404_NOT_FOUND
                )
            
            # Get enrolled courses
            enrolled_courses = get_student_enrolled_courses(student_profile, current_semester, current_session)
            
            # Mock announcements data for now
            announcements_data = [
                {
                    'id': 1,
                    'title': 'Welcome to the Course',
                    'content': 'Welcome to this semester. Please review the syllabus.',
                    'course': CourseSerializer(enrolled_courses.first()).data if enrolled_courses.exists() else None,
                    'is_general': False,
                    'created_by': 'Dr. Smith',
                    'created_at': '2024-01-15T10:00:00Z',
                    'is_read': False
                }
            ]
            
            return Response({
                'total_announcements': len(announcements_data),
                'unread_announcements': len([a for a in announcements_data if not a['is_read']]),
                'current_semester': current_semester.name,
                'current_session': current_session.session_name if current_session else None,
                'announcements': announcements_data
            }, status=status.HTTP_200_OK)
            
        except StudentProfile.DoesNotExist:
            return Response(
                {'detail': 'Student profile not found.'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {'detail': f'Error retrieving announcements: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class StudentCourseDetails(APIView):
    """
    View that returns detailed information for a specific course.
    """
    def get(self, request, course_id, *args, **kwargs):
        try:
            student_profile = StudentProfile.objects.get(user=request.user)
            current_semester = Semester.objects.filter(is_current=True).first()
            current_session = AcademicSession.objects.filter(is_current=True).first()
            
            if not current_semester:
                return Response(
                    {"detail": "No current semester set."}, 
                    status=status.HTTP_404_NOT_FOUND
                )
            
            # Verify student is enrolled in this course
            enrolled_courses = get_student_enrolled_courses(student_profile, current_semester, current_session)
            course = get_object_or_404(
                Course.objects.select_related('department', 'level', 'semester'),
                id=course_id
            )
            
            # Check if student is enrolled in this course
            if course not in enrolled_courses:
                return Response(
                    {"detail": "You are not enrolled in this course."},
                    status=status.HTTP_403_FORBIDDEN
                )
            
            # Get assignments for this course
            assignments = Assignment.objects.filter(
                course=course,
                is_published=True
            ).order_by('-created_at')
            
            # Calculate assignment stats
            total_assignments = assignments.count()
            total_points = sum([assignment.max_points for assignment in assignments])
            
            # Count pending assignments (not submitted)
            pending_assignments = Assignment.objects.filter(
                course=course,
                is_published=True
            ).exclude(
                submissions__student=student_profile,
                submissions__status='submitted'
            ).count()
            
            # Get grades for this course (mock for now)
            grades_data = [
                {
                    'id': 1,
                    'course': CourseSerializer(course).data,
                    'grade': 'A',
                    'grade_point': 4.0,
                    'total_points': 100,
                    'earned_points': 95,
                    'feedback': 'Excellent work!',
                    'graded_at': '2024-01-15T10:00:00Z',
                    'semester': current_semester.name,
                    'academic_session': current_session.session_name if current_session else None
                }
            ]
            
            # Get announcements for this course (mock for now)
            announcements_data = [
                {
                    'id': 1,
                    'title': f'Welcome to {course.title}',
                    'content': f'Welcome to {course.title}. Please review the syllabus.',
                    'course': CourseSerializer(course).data,
                    'is_general': False,
                    'created_by': 'Dr. Smith',
                    'created_at': '2024-01-15T10:00:00Z',
                    'is_read': False
                }
            ]
            
            return Response({
                'course': CourseSerializer(course).data,
                'assignments': [AssignmentSerializer(assignment).data for assignment in assignments],
                'grades': grades_data,
                'announcements': announcements_data,
                'total_assignments': total_assignments,
                'pending_assignments': pending_assignments,
                'total_points': total_points,
                'current_semester': current_semester.name,
                'current_session': current_session.session_name if current_session else None
            }, status=status.HTTP_200_OK)
            
        except StudentProfile.DoesNotExist:
            return Response(
                {'detail': 'Student profile not found.'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {'detail': f'Error retrieving course details: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class StudentAssignmentDetails(APIView):
    """
    View that returns detailed information for a specific assignment.
    """
    def get(self, request, assignment_id, *args, **kwargs):
        try:
            student_profile = StudentProfile.objects.get(user=request.user)
            current_semester = Semester.objects.filter(is_current=True).first()
            current_session = AcademicSession.objects.filter(is_current=True).first()
            
            if not current_semester:
                return Response(
                    {"detail": "No current semester set."}, 
                    status=status.HTTP_404_NOT_FOUND
                )
            
            # Get assignment and verify student is enrolled in the course
            enrolled_courses = get_student_enrolled_courses(student_profile, current_semester, current_session)
            assignment = get_object_or_404(
                Assignment.objects.select_related('course', 'created_by'),
                id=assignment_id
            )
            
            # Check if student is enrolled in the course for this assignment
            if assignment.course not in enrolled_courses:
                return Response(
                    {"detail": "You are not enrolled in this course."},
                    status=status.HTTP_403_FORBIDDEN
                )
            
            # Get student's submission for this assignment
            submission = AssignmentSubmission.objects.filter(
                assignment=assignment,
                student=student_profile
            ).first()
            
            return Response({
                'assignment': AssignmentSerializer(assignment).data,
                'submission': submission,
                'current_semester': current_semester.name,
                'current_session': current_session.session_name if current_session else None
            }, status=status.HTTP_200_OK)
            
        except StudentProfile.DoesNotExist:
            return Response(
                {'detail': 'Student profile not found.'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {'detail': f'Error retrieving assignment details: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class SubmitAssignment(APIView):
    """
    View for students to submit assignments.
    """
    def post(self, request, assignment_id, *args, **kwargs):
        try:
            student_profile = StudentProfile.objects.get(user=request.user)
            current_semester = Semester.objects.filter(is_current=True).first()
            current_session = AcademicSession.objects.filter(is_current=True).first()
            
            if not current_semester:
                return Response(
                    {"detail": "No current semester set."}, 
                    status=status.HTTP_404_NOT_FOUND
                )
            
            # Get assignment and verify student is enrolled in the course
            enrolled_courses = get_student_enrolled_courses(student_profile, current_semester, current_session)
            assignment = get_object_or_404(
                Assignment.objects.select_related('course'),
                id=assignment_id
            )
            
            # Check if student is enrolled in the course for this assignment
            if assignment.course not in enrolled_courses:
                return Response(
                    {"detail": "You are not enrolled in this course."},
                    status=status.HTTP_403_FORBIDDEN
                )
            
            # Check if assignment is still open
            from django.utils import timezone
            if assignment.due_date < timezone.now():
                return Response(
                    {"detail": "Assignment deadline has passed."},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Create or update submission
            submission_data = request.data.copy()
            submission_data['assignment'] = assignment.id
            submission_data['student'] = student_profile.id
            submission_data['status'] = 'submitted'
            
            # Check if submission already exists
            existing_submission = AssignmentSubmission.objects.filter(
                assignment=assignment,
                student=student_profile
            ).first()
            
            if existing_submission:
                serializer = AssignmentSubmissionSerializer(existing_submission, data=submission_data)
            else:
                serializer = AssignmentSubmissionSerializer(data=submission_data)
            
            if serializer.is_valid():
                submission = serializer.save()
                return Response({
                    'message': 'Assignment submitted successfully',
                    'submission': AssignmentSubmissionSerializer(submission).data
                }, status=status.HTTP_201_CREATED)
            else:
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
                
        except StudentProfile.DoesNotExist:
            return Response(
                {'detail': 'Student profile not found.'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {'detail': f'Error submitting assignment: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
