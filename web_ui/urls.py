"""URL configuration for the Web UI application."""

from django.contrib.auth.views import LoginView, LogoutView
from django.urls import path

from . import views

app_name = 'web_ui'

urlpatterns = [
    path('', views.home, name='home'),
    path('profile/', views.profile, name='profile'),
    path('admin-panel/', views.admin_panel, name='admin_panel'),
    path('about/', views.about, name='about'),
    path('health/', views.health, name='health'),
    path('network-info/', views.network_info, name='network_info'),
    path('login/', LoginView.as_view(template_name='web_ui/login.html'), name='login'),
    path('logout/', LogoutView.as_view(), name='logout'),
]
