# serializers.py
from django.contrib.auth import authenticate
from rest_framework import serializers

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
