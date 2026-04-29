from django.contrib import admin
from django.shortcuts import render
from django.urls import path
from django.contrib.admin.forms import AdminAuthenticationForm
from .models import Scan, UserProfile

class DietaryAdminSite(admin.AdminSite):
    site_header = "Dietary Inspector AI Admin"
    site_title = "Admin Portal"
    index_title = "Welcome to the AI Control Center"
    
    # This ensures that if a non-staff user tries to access /admin, 
    # they are prompted to login as an admin instead of just getting an error.
    login_form = AdminAuthenticationForm

    def has_permission(self, request):
        """
        Only users with is_staff=True can access the admin dashboard.
        """
        return request.user.is_active and request.user.is_staff

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('analytics/', self.admin_view(self.analytics_view), name="analytics"),
        ]
        return custom_urls + urls

    def analytics_view(self, request):
        # Calculate system-wide stats for the admin
        context = dict(
           self.each_context(request),
           total_scans=Scan.objects.count() if 'Scan' in globals() else 0,
           recent_alerts=Scan.objects.filter(rating='Red').count() if 'Scan' in globals() else 0,
           ai_model="Gemini 2.5 Flash",
        )
        return render(request, 'admin/analytics.html', context)

# Initialize the custom admin site
admin_site = DietaryAdminSite(name='dietary_admin')

@admin.register(Scan, site=admin_site)
class ScanAdmin(admin.ModelAdmin):
    list_display = ('user', 'product_name', 'rating', 'created_at')
    list_filter = ('rating', 'created_at')
    search_fields = ('product_name', 'user__username')

@admin.register(UserProfile, site=admin_site)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'allergies', 'health_goals')