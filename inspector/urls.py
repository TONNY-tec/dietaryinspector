# inspector/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('login/', views.login_view, name='login'),
    path('signup/', views.signup, name='signup'),
    path('logout/', views.logout_view, name='logout'),
    path('verify-otp/', views.verify_otp, name='verify_otp'),
    path('profile/', views.profile_view, name='profile'),
    path('settings/', views.settings_view, name='settings'),
    path('dashboard/', views.dashboard_view, name='dashboard'),
    path('allergen/', views.allergen_detector_view, name='allergen'),
    # path('scanner/', views.scanner_componet, name='scanner_componet'),
    path('management/dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('management/toggle-premium/<int:profile_id>/', views.toggle_premium, name='toggle_premium'),
    
    path('scan-api/', views.scan_api, name='scan_api'),
    path('recommendations/', views.recommendation_page, name='recommendations'),
    path('recommend-api/', views.recommend_api, name='recommend_api'),
    path('delete-recommendation/<int:pk>/', views.delete_recommendation, name='delete_recommendation'),
    
    path('api/guardian/talk/', views.guardian_talk_api, name='guardian_talk_api'),
    path('contact/', views.contact_view, name='contact'),
    path('pricing/', views.pricing_view, name='pricing'),

    path('api/payment/mpesa/stk-push/', views.initiate_stk_push, name='stk_push'),
    path('api/payment/mpesa/callback/', views.mpesa_callback, name='mpesa_callback'),

]