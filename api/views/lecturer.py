from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
from django.db.models import Count, Q, Sum
from ..models import *
from ..serializers import *

class LecturerOverview(APIView):
    """
    View that returns the lecturer's profile along with the current academic session.
    """
    def get(self, request, *args, **kwargs):
        try:
            lecturer_profile = LecturerProfile.objects.get(user=request.user)
            current_session = AcademicSession.objects.filter(is_current=True).first()
            lecturer_profile_serializer = LecturerProfileSerializer(lecturer_profile)
            current_session_serializer = AcademicSessionSerializer(current_session)
            semester = Semester.objects.get(is_current=True)

            return Response({
                'current_semester': semester.name,
                'lecturer_profile': lecturer_profile_serializer.data,
                'current_academic_session': current_session_serializer.data
            }, status=status.HTTP_200_OK)
        
        except LecturerProfile.DoesNotExist:
            return Response(
                {'detail': 'Lecturer profile not found.'},
                status=status.HTTP_404_NOT_FOUND
            )
        except AcademicSession.DoesNotExist:
            return Response(
                {'detail': 'No current academic session found.'},
                status=status.HTTP_404_NOT_FOUND
            )

class LmsOverview(APIView):
    """
    View that returns all courses assigned to the lecturer with statistics.
    """
    def get(self, request, *args, **kwargs):
        try:
            lecturer_profile = LecturerProfile.objects.get(user=request.user)
            current_semester = Semester.objects.filter(is_current=True).first()
            current_session = AcademicSession.objects.filter(is_current=True).first()
            
            if not current_semester:
                return Response(
                    {"detail": "No current semester set."}, 
                    status=status.HTTP_404_NOT_FOUND
                )
            
            # Get assigned courses for current semester
            assigned_courses = Course.objects.filter(
                assigned_lecturers=lecturer_profile,
                semester=current_semester
            ).select_related('department', 'level').prefetch_related('course_enrollments')
            
            # Calculate statistics
            total_courses = assigned_courses.count()
            
            # Count total students enrolled in assigned courses
            total_students = CourseEnrollment.objects.filter(
                course__in=assigned_courses,
                academic_session=current_session,
                semester=current_semester
            ).values('student').distinct().count()
            
            # Count total units (sum of all course units)
            total_units = assigned_courses.aggregate(
                total_units=Sum('units')
            )['total_units'] or 0
            
            # Serialize courses
            course_serializer = CourseSerializer(assigned_courses, many=True)
            
            return Response({
                'total_courses': total_courses,
                'total_students': total_students,
                'total_units': total_units,
                'current_semester': current_semester.name,
                'current_session': current_session.session_name if current_session else None,
                'courses': course_serializer.data
            }, status=status.HTTP_200_OK)
            
        except LecturerProfile.DoesNotExist:
            return Response(
                {'detail': 'Lecturer profile not found.'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {'detail': f'Error retrieving assigned courses: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class AllAssignments(APIView):
    """
    View that returns all assignments from all courses assigned to the lecturer with statistics.
    """
    def get(self, request, *args, **kwargs):
        try:
            lecturer_profile = LecturerProfile.objects.get(user=request.user)
            current_semester = Semester.objects.filter(is_current=True).first()
            current_session = AcademicSession.objects.filter(is_current=True).first()
            
            if not current_semester:
                return Response(
                    {"detail": "No current semester set."}, 
                    status=status.HTTP_404_NOT_FOUND
                )
            
            # Get assigned courses for current semester
            assigned_courses = Course.objects.filter(
                assigned_lecturers=lecturer_profile,
                semester=current_semester
            ).select_related('department', 'level')
            
            # Get all assignments from assigned courses
            assignments = Assignment.objects.filter(
                course__in=assigned_courses,
                created_by=lecturer_profile
            ).select_related('course', 'course__department').order_by('-created_at')
            
            # Calculate statistics
            total_assignments = assignments.count()
            published_assignments = assignments.filter(is_published=True).count()
            draft_assignments = assignments.filter(is_published=False).count()
            
            # Count assignments by type
            assignment_types = {}
            for assignment in assignments:
                assignment_type = assignment.assignment_type
                assignment_types[assignment_type] = assignment_types.get(assignment_type, 0) + 1
            
            # Serialize assignments
            assignment_serializer = AssignmentSerializer(assignments, many=True)
            
            return Response({
                'total_assignments': total_assignments,
                'published_assignments': published_assignments,
                'draft_assignments': draft_assignments,
                'assignment_types': assignment_types,
                'current_semester': current_semester.name,
                'current_session': current_session.session_name if current_session else None,
                'assignments': assignment_serializer.data
            }, status=status.HTTP_200_OK)
            
        except LecturerProfile.DoesNotExist:
            return Response(
                {'detail': 'Lecturer profile not found.'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {'detail': f'Error retrieving assignments: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class CourseManagement(APIView):
    """
    View that returns detailed course information for management.
    """
    def get(self, request, course_id, *args, **kwargs):
        try:
            lecturer_profile = LecturerProfile.objects.get(user=request.user)
            current_semester = Semester.objects.filter(is_current=True).first()
            current_session = AcademicSession.objects.filter(is_current=True).first()
            
            if not current_semester:
                return Response(
                    {"detail": "No current semester set."}, 
                    status=status.HTTP_404_NOT_FOUND
                )
            
            # Get the specific course and verify lecturer is assigned to it
            course = get_object_or_404(
                Course.objects.select_related('department', 'level', 'semester'),
                id=course_id,
                assigned_lecturers=lecturer_profile,
                semester=current_semester
            )
            
            # Get course statistics
            total_students = CourseEnrollment.objects.filter(
                course=course,
                academic_session=current_session,
                semester=current_semester
            ).count()
            
            # Mock data for additional course stats (to be replaced with real data later)
            assignments_count = 5  # TODO: Calculate from Assignment model
            announcements_count = 3  # TODO: Calculate from Announcement model
            pending_grades = 8  # TODO: Calculate from Grade model
            attendance_rate = 92  # TODO: Calculate from Attendance model
            
            # Serialize course
            course_serializer = CourseSerializer(course)
            
            return Response({
                'course': course_serializer.data,
                'current_semester': current_semester.name,
                'current_session': current_session.session_name if current_session else None,
                'course_stats': {
                    'total_students': total_students,
                    'assignments_count': assignments_count,
                    'announcements_count': announcements_count,
                    'pending_grades': pending_grades,
                    'attendance_rate': attendance_rate,
                }
            }, status=status.HTTP_200_OK)
            
        except LecturerProfile.DoesNotExist:
            return Response(
                {'detail': 'Lecturer profile not found.'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {'detail': f'Error retrieving course management data: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class CourseAssignments(APIView):
    """
    View to list and create assignments for a specific course
    """
    def get(self, request, course_id, *args, **kwargs):
        """
        Get all assignments for a specific course
        """
        try:
            lecturer_profile = LecturerProfile.objects.get(user=request.user)
            current_semester = Semester.objects.filter(is_current=True).first()
            
            if not current_semester:
                return Response(
                    {"detail": "No current semester set."}, 
                    status=status.HTTP_404_NOT_FOUND
                )
            
            # Verify lecturer is assigned to this course
            course = get_object_or_404(
                Course.objects.select_related('department', 'level', 'semester'),
                id=course_id,
                assigned_lecturers=lecturer_profile,
                semester=current_semester
            )
            
            # Get assignments for this course
            assignments = Assignment.objects.filter(
                course=course,
                created_by=lecturer_profile
            ).order_by('-created_at')
            
            # Serialize assignments
            assignment_serializer = AssignmentSerializer(assignments, many=True)
            
            return Response({
                'course': {
                    'id': course.id,
                    'code': course.code,
                    'title': course.title,
                },
                'assignments': assignment_serializer.data,
                'total_assignments': assignments.count(),
            }, status=status.HTTP_200_OK)
            
        except LecturerProfile.DoesNotExist:
            return Response(
                {'detail': 'Lecturer profile not found.'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {'detail': f'Error retrieving assignments: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def post(self, request, course_id, *args, **kwargs):
        """
        Create a new assignment for a specific course
        """
        try:
            lecturer_profile = LecturerProfile.objects.get(user=request.user)
            current_semester = Semester.objects.filter(is_current=True).first()
            
            if not current_semester:
                return Response(
                    {"detail": "No current semester set."}, 
                    status=status.HTTP_404_NOT_FOUND
                )
            
            # Verify lecturer is assigned to this course
            course = get_object_or_404(
                Course,
                id=course_id,
                assigned_lecturers=lecturer_profile,
                semester=current_semester
            )
            
            # Add course_id and created_by to request data
            assignment_data = request.data.copy()
            assignment_data['course_id'] = course_id
            assignment_data['created_by_id'] = lecturer_profile.id
            
            # Serialize and validate assignment data
            serializer = AssignmentSerializer(data=assignment_data)
            if serializer.is_valid():
                assignment = serializer.save()
                return Response({
                    'message': 'Assignment created successfully',
                    'assignment': AssignmentSerializer(assignment).data
                }, status=status.HTTP_201_CREATED)
            else:
                return Response({
                    'error': 'Invalid assignment data',
                    'details': serializer.errors
                }, status=status.HTTP_400_BAD_REQUEST)
                
        except LecturerProfile.DoesNotExist:
            return Response(
                {'detail': 'Lecturer profile not found.'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {'detail': f'Error creating assignment: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class AssignmentDetail(APIView):
    """
    View to get, update, or delete a specific assignment
    """
    def get(self, request, course_id, assignment_id, *args, **kwargs):
        """
        Get a specific assignment
        """
        try:
            lecturer_profile = LecturerProfile.objects.get(user=request.user)
            current_semester = Semester.objects.filter(is_current=True).first()
            
            if not current_semester:
                return Response(
                    {"detail": "No current semester set."}, 
                    status=status.HTTP_404_NOT_FOUND
                )
            
            # Verify lecturer is assigned to this course
            course = get_object_or_404(
                Course,
                id=course_id,
                assigned_lecturers=lecturer_profile,
                semester=current_semester
            )
            
            # Get the specific assignment
            assignment = get_object_or_404(
                Assignment,
                id=assignment_id,
                course=course,
                created_by=lecturer_profile
            )
            
            # Serialize assignment
            assignment_serializer = AssignmentSerializer(assignment)
            
            return Response({
                'assignment': assignment_serializer.data
            }, status=status.HTTP_200_OK)
            
        except LecturerProfile.DoesNotExist:
            return Response(
                {'detail': 'Lecturer profile not found.'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {'detail': f'Error retrieving assignment: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def put(self, request, course_id, assignment_id, *args, **kwargs):
        """
        Update a specific assignment
        """
        try:
            lecturer_profile = LecturerProfile.objects.get(user=request.user)
            current_semester = Semester.objects.filter(is_current=True).first()
            
            if not current_semester:
                return Response(
                    {"detail": "No current semester set."}, 
                    status=status.HTTP_404_NOT_FOUND
                )
            
            # Verify lecturer is assigned to this course
            course = get_object_or_404(
                Course,
                id=course_id,
                assigned_lecturers=lecturer_profile,
                semester=current_semester
            )
            
            # Get the specific assignment
            assignment = get_object_or_404(
                Assignment,
                id=assignment_id,
                course=course,
                created_by=lecturer_profile
            )
            
            # Add course_id and created_by to request data
            assignment_data = request.data.copy()
            assignment_data['course_id'] = course_id
            assignment_data['created_by_id'] = lecturer_profile.id
            
            # Serialize and validate assignment data
            serializer = AssignmentSerializer(assignment, data=assignment_data)
            if serializer.is_valid():
                updated_assignment = serializer.save()
                return Response({
                    'message': 'Assignment updated successfully',
                    'assignment': AssignmentSerializer(updated_assignment).data
                }, status=status.HTTP_200_OK)
            else:
                return Response({
                    'error': 'Invalid assignment data',
                    'details': serializer.errors
                }, status=status.HTTP_400_BAD_REQUEST)
                
        except LecturerProfile.DoesNotExist:
            return Response(
                {'detail': 'Lecturer profile not found.'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {'detail': f'Error updating assignment: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def delete(self, request, course_id, assignment_id, *args, **kwargs):
        """
        Delete a specific assignment
        """
        try:
            lecturer_profile = LecturerProfile.objects.get(user=request.user)
            current_semester = Semester.objects.filter(is_current=True).first()
            
            if not current_semester:
                return Response(
                    {"detail": "No current semester set."}, 
                    status=status.HTTP_404_NOT_FOUND
                )
            
            # Verify lecturer is assigned to this course
            course = get_object_or_404(
                Course,
                id=course_id,
                assigned_lecturers=lecturer_profile,
                semester=current_semester
            )
            
            # Get the specific assignment
            assignment = get_object_or_404(
                Assignment,
                id=assignment_id,
                course=course,
                created_by=lecturer_profile
            )
            
            assignment.delete()
            
            return Response({
                'message': 'Assignment deleted successfully'
            }, status=status.HTTP_204_NO_CONTENT)
            
        except LecturerProfile.DoesNotExist:
            return Response(
                {'detail': 'Lecturer profile not found.'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {'detail': f'Error deleting assignment: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class CourseStudents(APIView):
    """
    View to get all students enrolled in a specific course
    """
    def get(self, request, course_id, *args, **kwargs):
        try:
            lecturer_profile = LecturerProfile.objects.get(user=request.user)
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
            
            # Verify lecturer is assigned to this course
            course = get_object_or_404(
                Course.objects.select_related('department', 'level', 'semester'),
                id=course_id,
                assigned_lecturers=lecturer_profile,
                semester=current_semester
            )
            
            # Get all students enrolled in this course for current semester/session
            enrollments = CourseEnrollment.objects.filter(
                course=course,
                academic_session=current_session,
                semester=current_semester
            ).select_related('student', 'student__department', 'student__level').order_by('student__matric_number')
            
            # Get unique students (in case of duplicates)
            students_data = []
            seen_students = set()
            
            for enrollment in enrollments:
                student = enrollment.student
                if student.id not in seen_students:
                    seen_students.add(student.id)
                    students_data.append({
                        'id': student.id,
                        'full_name': student.full_name,
                        'matric_number': student.matric_number,
                        'department': student.department.name if student.department else None,
                        'level': student.level.name if student.level else None,
                        'cgpa': float(student.cgpa) if student.cgpa else None,
                        'grade': enrollment.grade if enrollment.grade else None,
                        'grade_point': float(enrollment.grade_point) if enrollment.grade_point else None,
                    })
            
            # Serialize course
            course_serializer = CourseSerializer(course)
            
            return Response({
                'course': course_serializer.data,
                'current_semester': current_semester.name,
                'current_session': current_session.session_name if current_session else None,
                'total_students': len(students_data),
                'students': students_data
            }, status=status.HTTP_200_OK)
            
        except LecturerProfile.DoesNotExist:
            return Response(
                {'detail': 'Lecturer profile not found.'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {'detail': f'Error retrieving course students: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class CourseAnnouncements(APIView):
    """
    View to get and create announcements for a specific course
    """
    def get(self, request, course_id, *args, **kwargs):
        try:
            lecturer_profile = LecturerProfile.objects.get(user=request.user)
            current_semester = Semester.objects.filter(is_current=True).first()
            
            if not current_semester:
                return Response(
                    {"detail": "No current semester set."}, 
                    status=status.HTTP_404_NOT_FOUND
                )
            
            # Verify lecturer is assigned to this course
            course = get_object_or_404(
                Course.objects.select_related('department', 'level', 'semester'),
                id=course_id,
                assigned_lecturers=lecturer_profile,
                semester=current_semester
            )
            
            # Get announcements for this course
            announcements = Announcement.objects.filter(
                course=course
            ).select_related('created_by', 'course').order_by('-created_at')
            
            announcement_serializer = AnnouncementSerializer(announcements, many=True)
            
            return Response({
                'course': {
                    'id': course.id,
                    'code': course.code,
                    'title': course.title,
                },
                'total_announcements': announcements.count(),
                'announcements': announcement_serializer.data
            }, status=status.HTTP_200_OK)
            
        except LecturerProfile.DoesNotExist:
            return Response(
                {'detail': 'Lecturer profile not found.'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {'detail': f'Error retrieving announcements: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def post(self, request, course_id, *args, **kwargs):
        try:
            lecturer_profile = LecturerProfile.objects.get(user=request.user)
            current_semester = Semester.objects.filter(is_current=True).first()
            
            if not current_semester:
                return Response(
                    {"detail": "No current semester set."}, 
                    status=status.HTTP_404_NOT_FOUND
                )
            
            # Verify lecturer is assigned to this course
            course = get_object_or_404(
                Course,
                id=course_id,
                assigned_lecturers=lecturer_profile,
                semester=current_semester
            )
            
            # Add course_id and created_by to request data
            announcement_data = request.data.copy()
            announcement_data['course_id'] = course_id
            announcement_data['created_by_id'] = lecturer_profile.id
            announcement_data['is_general'] = False
            
            # Serialize and validate announcement data
            serializer = AnnouncementSerializer(data=announcement_data)
            if serializer.is_valid():
                announcement = serializer.save()
                return Response({
                    'message': 'Announcement created successfully',
                    'announcement': AnnouncementSerializer(announcement).data
                }, status=status.HTTP_201_CREATED)
            else:
                return Response({
                    'error': 'Invalid announcement data',
                    'details': serializer.errors
                }, status=status.HTTP_400_BAD_REQUEST)
                
        except LecturerProfile.DoesNotExist:
            return Response(
                {'detail': 'Lecturer profile not found.'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {'detail': f'Error creating announcement: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class GeneralAnnouncements(APIView):
    """
    View to get all announcements (both general and course-specific) and create general announcements
    """
    def get(self, request, *args, **kwargs):
        try:
            lecturer_profile = LecturerProfile.objects.get(user=request.user)
            current_semester = Semester.objects.filter(is_current=True).first()
            
            # Get all announcements - both general and course-specific
            # For course-specific, only show announcements for courses assigned to this lecturer
            assigned_courses = Course.objects.filter(
                assigned_lecturers=lecturer_profile,
                semester=current_semester
            ) if current_semester else Course.objects.filter(assigned_lecturers=lecturer_profile)
            
            announcements = Announcement.objects.filter(
                Q(is_general=True) | Q(course__in=assigned_courses)
            ).select_related('created_by', 'course').order_by('-created_at')
            
            announcement_serializer = AnnouncementSerializer(announcements, many=True)
            
            return Response({
                'total_announcements': announcements.count(),
                'announcements': announcement_serializer.data
            }, status=status.HTTP_200_OK)
            
        except LecturerProfile.DoesNotExist:
            return Response(
                {'detail': 'Lecturer profile not found.'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {'detail': f'Error retrieving announcements: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def post(self, request, *args, **kwargs):
        try:
            lecturer_profile = LecturerProfile.objects.get(user=request.user)
            current_semester = Semester.objects.filter(is_current=True).first()
            
            if not current_semester:
                return Response(
                    {"detail": "No current semester set."}, 
                    status=status.HTTP_404_NOT_FOUND
                )
            
            # Get assigned courses for current semester
            assigned_courses = Course.objects.filter(
                assigned_lecturers=lecturer_profile,
                semester=current_semester
            )
            
            # Add created_by to request data
            announcement_data = request.data.copy()
            announcement_data['created_by_id'] = lecturer_profile.id
            
            # Determine if general or course-specific
            course_id = announcement_data.get('course_id')
            if course_id:
                # Verify lecturer is assigned to this course
                course = get_object_or_404(
                    assigned_courses,
                    id=course_id
                )
                announcement_data['is_general'] = False
            else:
                announcement_data['is_general'] = True
            
            # Serialize and validate announcement data
            serializer = AnnouncementSerializer(data=announcement_data)
            if serializer.is_valid():
                announcement = serializer.save()
                return Response({
                    'message': 'Announcement created successfully',
                    'announcement': AnnouncementSerializer(announcement).data
                }, status=status.HTTP_201_CREATED)
            else:
                return Response({
                    'error': 'Invalid announcement data',
                    'details': serializer.errors
                }, status=status.HTTP_400_BAD_REQUEST)
                
        except LecturerProfile.DoesNotExist:
            return Response(
                {'detail': 'Lecturer profile not found.'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {'detail': f'Error creating announcement: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


