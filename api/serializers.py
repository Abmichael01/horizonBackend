# serializers.py
from django.contrib.auth import authenticate
from rest_framework import serializers
from .models.models import *
from datetime import datetime

class UserSerializer(serializers.ModelSerializer):
    user_type = serializers.ReadOnlyField()
    
    class Meta:
        model = User
        fields = ["email", "date_joined", "user_type"]

class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

    def validate(self, data):
        email = data.get("email")
        password = data.get("password")

        # Authenticate the user with email and password
        user = authenticate(email=email, password=password)

        if user is None:
            raise serializers.ValidationError("Invalid credentials. Please try again.")

        # Return the user object (to be used later for token generation, etc.)
        data["user"] = user
        return data

class AcademicSessionSerializer(serializers.ModelSerializer):
    class Meta:
        model = AcademicSession
        fields = ['session_name', 'start_date', 'end_date']
        
class FacultySerializer(serializers.ModelSerializer):
    class Meta:
        model = Faculty
        fields = ['id', 'name']

class DepartmentSerializer(serializers.ModelSerializer):
    faculty = FacultySerializer(read_only=True)
    class Meta:
        model = Department
        fields = ['id', 'name', 'short', 'created_at', 'faculty']

class LevelSerializer(serializers.ModelSerializer):
    class Meta:
        model = Level
        fields = ['id', 'name']
        
class CourseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Course
        fields = ['id', 'code', 'title', 'units', 'department']        

class SemesterSerializer(serializers.ModelSerializer):
    class Meta:
        model = Semester
        fields = ['id', 'name', 'is_current']

class StudentProfileSerializer(serializers.ModelSerializer):
    department = DepartmentSerializer(read_only=True)
    department_id = serializers.PrimaryKeyRelatedField(
        queryset=Department.objects.all(), source='department', write_only=True
    )
    user = UserSerializer(read_only=True)
    level = serializers.CharField(source='level.name', read_only=True)

    class Meta:
        model = StudentProfile
        fields = [
            'id',
            'user',
            'full_name',
            'matric_number',
            'dob',
            'cgpa',
            'phone',
            'department',
            'department_id',
            'level',
            'created_at',
        ]

class CourseEnrollmentSerializer(serializers.ModelSerializer):
    course = CourseSerializer(read_only=True)
    # student = StudentProfileSerializer(read_only=True)
    
    class Meta:
        model = CourseEnrollment
        fields = ['id', 'course', 'grade', 'grade_point', 'academic_session', 'semester', 'date_recorded']

class CourseRegistrationSerializer(serializers.ModelSerializer):
    courses = CourseEnrollmentSerializer(many=True, read_only=True)
    student = StudentProfileSerializer(read_only=True)
    
    class Meta:
        model = CourseRegistration
        fields = ['id', 'student', 'academic_session', 'semester', 'courses', 'enrollment_date', 'total_units', 'semester_gpa']




class CreateUserSerializer(serializers.Serializer):
    USER_TYPE_CHOICES = (
        ('student', 'Student'),
        ('lecturer', 'Lecturer'),
    )
    user_type = serializers.ChoiceField(choices=USER_TYPE_CHOICES)
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)
    full_name = serializers.CharField(max_length=100)
    phone = serializers.CharField(max_length=20, allow_blank=True, required=False)
    department = serializers.PrimaryKeyRelatedField(
        queryset=Department.objects.all()
    )
    # Student specific fields
    dob = serializers.DateField(required=False)
    level = serializers.PrimaryKeyRelatedField(
        queryset=Level.objects.all(),
        required=False
    )
    # Lecturer specific fields
    specialization = serializers.CharField(max_length=200, allow_blank=True, required=False)

    def validate(self, attrs):
        # You can add custom validation here if needed
        return attrs

    def generate_matric_number(self):
        current_year = datetime.now().year
        prefix = f"HRZ{current_year}"
        # Find the last matric_number for this year
        last_profile = StudentProfile.objects.filter(
            matric_number__startswith=prefix
        ).order_by('-matric_number').first()
        if last_profile and last_profile.matric_number[len(prefix):].isdigit():
            last_number = int(last_profile.matric_number[len(prefix):])
        else:
            last_number = 0
        new_number = last_number + 1
        return f"{prefix}{str(new_number).zfill(5)}"

    def create(self, validated_data):
        user_type = validated_data.pop('user_type')
        email = validated_data.pop('email')
        password = validated_data.pop('password')

        # Create the user
        user = User.objects.create_user(email=email, password=password)
        
        if user_type == 'student':
            matric_number = self.generate_matric_number()
            StudentProfile.objects.create(
                user=user,
                full_name=validated_data.get('full_name'),
                matric_number=matric_number,
                dob=validated_data.get('dob'),
                phone=validated_data.get('phone', ''),
                department=validated_data.get('department'),
                level=validated_data.get('level'),
            )
        elif user_type == 'lecturer':
            from .models.models import LecturerProfile
            LecturerProfile.objects.create(
                user=user,
                full_name=validated_data.get('full_name'),
                phone=validated_data.get('phone', ''),
                department=validated_data.get('department'),
                specialization=validated_data.get('specialization', ''),
            )

        return user
