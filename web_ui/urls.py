"""URL configuration for the Web UI application."""

from django.urls import path

from . import views

app_name = 'web_ui'

urlpatterns = [
    path('', views.home, name='home'),
    path('health/', views.health, name='health'),
    path('network-info/', views.network_info, name='network_info'),
]
