# serializers.py
from django.contrib.auth import authenticate
from rest_framework import serializers
from .models import Department, StudentProfile

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


class DepartmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Department
        fields = ['id', 'name', 'short', 'created_at']

class StudentProfileSerializer(serializers.ModelSerializer):
    department = DepartmentSerializer(read_only=True)
    department_id = serializers.PrimaryKeyRelatedField(
        queryset=Department.objects.all(), source='department', write_only=True
    )

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