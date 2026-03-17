# inspector/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('login/', views.login_view, name='login'),
    path('signup/', views.signup, name='signup'),
    path('logout/', views.logout_view, name='logout'),
    path('profile/', views.profile_view, name='profile'),
    path('allergen/', views.allergen_detector_view, name='allergen'),
    # path('scanner/', views.scanner_componet, name='scanner_componet'),
    path('scan-api/', views.scan_api, name='scan_api'),
    path('recommendations/', views.recommendation_page, name='recommendations'),
    path('recommend-api/', views.recommend_api, name='recommend_api'),
]