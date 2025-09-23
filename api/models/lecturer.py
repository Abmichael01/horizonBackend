from django.db import models
import random
import string
from .models import User, Department


def generate_lecturer_id():
    """Generate a unique 6-character ID for lecturer"""
    while True:
        # Generate 6 random alphanumeric characters
        lecturer_id = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
        full_id = f"LEC-{lecturer_id}"
        
        # Check if this ID already exists
        if not LecturerProfile.objects.filter(id=full_id).exists():
            return full_id


class LecturerProfile(models.Model):
    id = models.CharField(max_length=10, primary_key=True, default=generate_lecturer_id)
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='lecturer_profile')
    full_name = models.CharField(max_length=100)
    phone = models.CharField(max_length=20, blank=True)
    department = models.ForeignKey(
        Department, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='lecturers'
    )
    specialization = models.CharField(max_length=200, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    @property
    def staff_id(self):
        """Return the id as staff_id for consistency"""
        return self.id

    def __str__(self):
        return f"{self.full_name} ({self.id})"

    class Meta:
        ordering = ['id']
