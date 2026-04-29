from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    is_premium = models.BooleanField(default=False)
    subscription_start_date = models.DateTimeField(null=True, blank=True)
    subscription_end_date = models.DateTimeField(null=True, blank=True)
    daily_scan_count = models.IntegerField(default=0)
    last_scan_date = models.DateField(auto_now=True)
    otp_code = models.CharField(max_length=6, blank=True, null=True)
    otp_created_at = models.DateTimeField(blank=True, null=True)
    is_verified = models.BooleanField(default=False)
    
    # Personal Context Fields
    allergies = models.TextField(blank=True, help_text="e.g., Peanuts, Dairy")
    restrictions = models.TextField(blank=True, help_text="e.g., Gluten-Free, Vegan")
    health_goals = models.TextField(blank=True, help_text="e.g., Weight loss")

    def can_scan(self):
        today = timezone.now().date()
        if self.is_premium and self.subscription_end_date:
             if timezone.now() > self.subscription_end_date:
                self.is_premium = False
                self.save()

        if self.last_scan_date != today:
            self.daily_scan_count = 0
            self.last_scan_date = today
            self.save()
            
        if self.is_premium:
            return True
        return self.daily_scan_count < 2

    def __str__(self):
        return f"{self.user.username}'s Profile"

# NEW SEPARATED MODEL
class Recommendation(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='recommendations')
    query_text = models.TextField()
    recommendation_text = models.TextField()
    category = models.CharField(max_length=50, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Scan by {self.user.username} on {self.created_at.date()}"

# Signals remain the same as your provided code
@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(user=instance)

@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    instance.userprofile.save()


class Scan(models.Model):
    """
    Records of food scans performed by users.
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='scans')
    product_name = models.CharField(max_length=255)
    rating = models.CharField(max_length=20, choices=[('Green', 'Safe'), ('Amber', 'Caution'), ('Red', 'Unsafe')])
    analysis_summary = models.TextField()
    image_base64 = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.product_name} - {self.rating}"

class ContactMessage(models.Model):
    name = models.CharField(max_length=100)
    email = models.EmailField()
    subject = models.CharField(max_length=200)
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __clstr__(self):
        return f"{self.name} - {self.subject}"