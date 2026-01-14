from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver

# Create your models here.
class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    allergies = models.TextField(blank=True, help_text="e.g., Peanuts, Dairy, Shellfish")
    restrictions = models.TextField(blank=True, help_text="e.g., Gluten-Free, Vegan, Low-FODMAP")
    health_goals = models.TextField(blank=True, help_text="e.g., Weight loss, Muscle gain")

    def __clstr__(self):
        return f"{self.user.username}'s Profile"

# These signals automatically create a Profile whenever a New User is created
@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(user=instance)

@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    instance.userprofile.save()