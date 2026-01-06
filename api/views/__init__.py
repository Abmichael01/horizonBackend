from rest_framework import status
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from django.contrib.auth import get_user_model
from ..serializers import *
from ..models import *

User = get_user_model()

class CreateUserView(APIView):
    permission_classes = [AllowAny]
    
    def get(self, request):
        """
        Returns lists of departments and levels for user registration form
        """
        departments = Department.objects.all()
        levels = Level.objects.all()
        
        department_serializer = DepartmentSerializer(departments, many=True)
        level_serializer = LevelSerializer(levels, many=True)
        
        return Response({
            'departments': department_serializer.data,
            'levels': level_serializer.data
        })
    
    def post(self, request):
        """
        Creates a new user with student profile
        """
        serializer = CreateUserSerializer(data=request.data)
        if serializer.is_valid():
            try:
                user = serializer.save()
                return Response({
                    'message': 'User created successfully',
                    'user_id': user.id,
                    'email': user.email
                }, status=status.HTTP_201_CREATED)
            except Exception as e:
                return Response({
                    'error': 'Failed to create user',
                    'details': str(e)
                }, status=status.HTTP_400_BAD_REQUEST)
        else:
            return Response({
                'error': 'Invalid data',
                'details': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)

# Import all views from submodules
from .student import *
from .lecturer import *
